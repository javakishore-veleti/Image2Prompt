"""Chroma stack -> real when `chromadb` is importable; else in-process fallback."""

from __future__ import annotations

from ...config import settings
from .base import VectorStore, log


class ChromaVectorStore(VectorStore):
    stack = "chroma"

    def __init__(self):
        self._client = None
        try:
            import chromadb

            self._client = (
                chromadb.PersistentClient(path=settings.chroma_path)
                if settings.chroma_path
                else chromadb.EphemeralClient()
            )
        except Exception as exc:
            log.warning("chroma unavailable (%s); using in-process index", exc)

    def ready(self) -> bool:
        return self._client is not None

    def _coll(self, namespace):
        return self._client.get_or_create_collection(f"kb_{namespace}")

    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db=None):
        if not self._client:
            return self._mem_upsert(namespace, doc_id, vector, payload)
        try:
            self._coll(namespace).upsert(
                ids=[doc_id], embeddings=[vector], documents=[text or ""], metadatas=[payload or {}]
            )
        except Exception as exc:
            log.warning("chroma upsert failed (%s); using in-process index", exc)
            self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, text="", top_k=5, db=None):
        if not self._client:
            return self._mem_query(namespace, vector, top_k)
        try:
            res = self._coll(namespace).query(query_embeddings=[vector], n_results=top_k)
            ids = (res.get("ids") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            out = []
            for i, did in enumerate(ids):
                dist = dists[i] if i < len(dists) else 1.0
                out.append({"id": did, "score": 1.0 - float(dist), "payload": metas[i] if i < len(metas) else {}})
            return out
        except Exception as exc:
            log.warning("chroma query failed (%s); using in-process index", exc)
            return self._mem_query(namespace, vector, top_k)
