"""MongoDB Atlas Vector Search. Documents stored per (kb_id, doc_id); query uses the
$vectorSearch aggregation against a pre-created Atlas vector index. Degrades to the
in-process index (Atlas indexes can't be created via the driver)."""

from __future__ import annotations

from ...config import settings
from .base import VectorStore, log


class MongoVectorStore(VectorStore):
    stack = "mongodb"

    def __init__(self):
        self._coll = None
        if not settings.mongodb_uri:
            return
        try:
            from pymongo import MongoClient

            client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
            self._coll = client[settings.mongodb_db][settings.mongodb_collection]
        except Exception as exc:
            log.warning("mongodb unavailable (%s); using in-process index", exc)

    def ready(self) -> bool:
        return self._coll is not None

    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db=None):
        if self._coll is None:
            return self._mem_upsert(namespace, doc_id, vector, payload)
        try:
            self._coll.replace_one(
                {"_id": f"{namespace}:{doc_id}"},
                {"_id": f"{namespace}:{doc_id}", "kb_id": namespace, "doc_id": doc_id,
                 "embedding": vector, "payload": payload or {}, "text": text or ""},
                upsert=True,
            )
        except Exception as exc:
            log.warning("mongodb upsert failed (%s); using in-process index", exc)
            self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, text="", top_k=5, db=None):
        if self._coll is None:
            return self._mem_query(namespace, vector, top_k)
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": settings.mongodb_vector_index,
                        "path": "embedding",
                        "queryVector": vector,
                        "numCandidates": max(top_k * 10, 50),
                        "limit": top_k,
                        "filter": {"kb_id": namespace},
                    }
                },
                {"$project": {"doc_id": 1, "payload": 1, "score": {"$meta": "vectorSearchScore"}}},
            ]
            return [
                {"id": d.get("doc_id"), "score": float(d.get("score", 0.0)), "payload": d.get("payload", {})}
                for d in self._coll.aggregate(pipeline)
            ]
        except Exception as exc:
            log.warning("mongodb query failed (%s); using in-process index", exc)
            return self._mem_query(namespace, vector, top_k)
