"""Weaviate v4 vector store. One collection; KB id stored as a property and used to
filter queries. Collection created lazily. Degrades to the in-process index."""

from __future__ import annotations

from ...config import settings
from .base import VectorStore, log


class WeaviateStore(VectorStore):
    stack = "weaviate"

    def __init__(self):
        self._client = None
        if not settings.weaviate_url:
            return
        try:
            import weaviate
            from weaviate.classes.init import Auth

            auth = Auth.api_key(settings.weaviate_api_key) if settings.weaviate_api_key else None
            self._client = weaviate.connect_to_weaviate_cloud(
                cluster_url=settings.weaviate_url, auth_credentials=auth
            )
        except Exception as exc:
            log.warning("weaviate unavailable (%s); using in-process index", exc)

    def ready(self) -> bool:
        return self._client is not None

    def _collection(self):
        name = settings.weaviate_collection
        try:
            if not self._client.collections.exists(name):
                self._client.collections.create(name=name)
        except Exception as exc:
            log.warning("weaviate ensure-collection: %s", exc)
        return self._client.collections.get(name)

    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db=None):
        if self._client is None:
            return self._mem_upsert(namespace, doc_id, vector, payload)
        try:
            import uuid as _uuid

            uid = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"{namespace}:{doc_id}"))
            props = {"kb_id": namespace, "doc_id": doc_id, "title": (payload or {}).get("title", "")}
            self._collection().data.insert(properties=props, uuid=uid, vector=vector)
        except Exception as exc:
            log.warning("weaviate upsert failed (%s); using in-process index", exc)
            self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, text="", top_k=5, db=None):
        if self._client is None:
            return self._mem_query(namespace, vector, top_k)
        try:
            from weaviate.classes.query import Filter, MetadataQuery

            res = self._collection().query.near_vector(
                near_vector=vector, limit=top_k,
                filters=Filter.by_property("kb_id").equal(namespace),
                return_metadata=MetadataQuery(distance=True),
            )
            out = []
            for o in res.objects:
                dist = o.metadata.distance if o.metadata and o.metadata.distance is not None else 1.0
                out.append(
                    {"id": o.properties.get("doc_id"), "score": 1.0 - float(dist),
                     "payload": {"generation_id": o.properties.get("doc_id"), "title": o.properties.get("title")}}
                )
            return out
        except Exception as exc:
            log.warning("weaviate query failed (%s); using in-process index", exc)
            return self._mem_query(namespace, vector, top_k)

    def delete_namespace(self, *, namespace, db=None):
        self._mem_delete(namespace)
        if self._client is None:
            return
        try:
            from weaviate.classes.query import Filter

            self._collection().data.delete_many(
                where=Filter.by_property("kb_id").equal(namespace)
            )
        except Exception as exc:
            log.warning("weaviate delete_namespace failed: %s", exc)
