"""AWS OpenSearch k-NN vector store. Index per KB, created lazily with the
embedding dimension on first upsert. Degrades to the in-process index."""

from __future__ import annotations

from ...config import settings
from .base import VectorStore, log


class OpenSearchStore(VectorStore):
    stack = "opensearch"

    def __init__(self):
        self._client = None
        if not settings.opensearch_url:
            return
        try:
            from opensearchpy import OpenSearch

            kwargs = {"hosts": [settings.opensearch_url], "http_compress": True}
            if settings.opensearch_user:
                kwargs["http_auth"] = (settings.opensearch_user, settings.opensearch_password)
            self._client = OpenSearch(**kwargs)
        except Exception as exc:
            log.warning("opensearch unavailable (%s); using in-process index", exc)

    def ready(self) -> bool:
        return self._client is not None

    def _index(self, namespace: str) -> str:
        return f"{settings.opensearch_index_prefix}-{namespace}".lower()

    def _ensure_index(self, index: str, dim: int):
        if self._client.indices.exists(index=index):
            return
        self._client.indices.create(
            index=index,
            body={
                "settings": {"index": {"knn": True}},
                "mappings": {"properties": {"vector": {"type": "knn_vector", "dimension": dim}}},
            },
        )

    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db=None):
        if not self._client:
            return self._mem_upsert(namespace, doc_id, vector, payload)
        try:
            index = self._index(namespace)
            self._ensure_index(index, len(vector))
            self._client.index(
                index=index, id=doc_id,
                body={"vector": vector, "payload": payload or {}, "text": text or ""}, refresh=True,
            )
        except Exception as exc:
            log.warning("opensearch upsert failed (%s); using in-process index", exc)
            self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, text="", top_k=5, db=None):
        if not self._client:
            return self._mem_query(namespace, vector, top_k)
        try:
            index = self._index(namespace)
            res = self._client.search(
                index=index,
                body={"size": top_k, "query": {"knn": {"vector": {"vector": vector, "k": top_k}}}},
            )
            return [
                {"id": h["_id"], "score": float(h.get("_score", 0.0)), "payload": h["_source"].get("payload", {})}
                for h in res.get("hits", {}).get("hits", [])
            ]
        except Exception as exc:
            log.warning("opensearch query failed (%s); using in-process index", exc)
            return self._mem_query(namespace, vector, top_k)

    def delete_namespace(self, *, namespace, db=None):
        self._mem_delete(namespace)
        if not self._client:
            return
        try:
            index = self._index(namespace)
            if self._client.indices.exists(index=index):
                self._client.indices.delete(index=index)
        except Exception as exc:
            log.warning("opensearch delete_namespace failed: %s", exc)
