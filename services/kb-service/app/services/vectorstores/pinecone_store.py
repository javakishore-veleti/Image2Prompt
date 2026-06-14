"""Pinecone serverless vector store. One index, KB id as the namespace; the index
is created lazily with the embedding dimension. Degrades to the in-process index."""

from __future__ import annotations

from ...config import settings
from .base import VectorStore, log


class PineconeStore(VectorStore):
    stack = "pinecone"

    def __init__(self):
        self._pc = None
        if not settings.pinecone_api_key:
            return
        try:
            from pinecone import Pinecone

            self._pc = Pinecone(api_key=settings.pinecone_api_key)
        except Exception as exc:
            log.warning("pinecone unavailable (%s); using in-process index", exc)

    def ready(self) -> bool:
        return self._pc is not None

    def _index(self, dim: int):
        name = settings.pinecone_index
        try:
            from pinecone import ServerlessSpec

            existing = {i["name"] for i in self._pc.list_indexes()}
            if name not in existing:
                self._pc.create_index(
                    name=name, dimension=dim, metric="cosine",
                    spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
                )
        except Exception as exc:
            log.warning("pinecone ensure-index: %s", exc)
        return self._pc.Index(name)

    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db=None):
        if self._pc is None:
            return self._mem_upsert(namespace, doc_id, vector, payload)
        try:
            self._index(len(vector)).upsert(
                vectors=[{"id": doc_id, "values": vector, "metadata": payload or {}}], namespace=namespace
            )
        except Exception as exc:
            log.warning("pinecone upsert failed (%s); using in-process index", exc)
            self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, text="", top_k=5, db=None):
        if self._pc is None:
            return self._mem_query(namespace, vector, top_k)
        try:
            res = self._index(len(vector)).query(
                vector=vector, top_k=top_k, namespace=namespace, include_metadata=True
            )
            return [
                {"id": m["id"], "score": float(m.get("score", 0.0)), "payload": m.get("metadata", {})}
                for m in res.get("matches", [])
            ]
        except Exception as exc:
            log.warning("pinecone query failed (%s); using in-process index", exc)
            return self._mem_query(namespace, vector, top_k)
