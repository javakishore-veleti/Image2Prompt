"""neo4j vector index. Each KB doc is a (:KbDoc) node with an embedding; the vector
index is created lazily. Query uses db.index.vector.queryNodes. Degrades gracefully."""

from __future__ import annotations

from ...config import settings
from .base import VectorStore, log


class Neo4jVectorStore(VectorStore):
    stack = "neo4j"

    def __init__(self):
        self._driver = None
        if not settings.neo4j_uri:
            return
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
            )
        except Exception as exc:
            log.warning("neo4j unavailable (%s); using in-process index", exc)

    def ready(self) -> bool:
        return self._driver is not None

    def _ensure_index(self, session, dim: int):
        session.run(
            f"CREATE VECTOR INDEX {settings.neo4j_vector_index} IF NOT EXISTS "
            "FOR (d:KbDoc) ON (d.embedding) "
            "OPTIONS {indexConfig: {`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}",
            dim=dim,
        )

    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db=None):
        if self._driver is None:
            return self._mem_upsert(namespace, doc_id, vector, payload)
        try:
            with self._driver.session(database=settings.neo4j_database) as s:
                self._ensure_index(s, len(vector))
                s.run(
                    "MERGE (d:KbDoc {uid: $uid}) "
                    "SET d.kb_id=$kb, d.doc_id=$doc, d.embedding=$emb, d.title=$title",
                    uid=f"{namespace}:{doc_id}", kb=namespace, doc=doc_id, emb=vector,
                    title=(payload or {}).get("title", ""),
                )
        except Exception as exc:
            log.warning("neo4j upsert failed (%s); using in-process index", exc)
            self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, text="", top_k=5, db=None):
        if self._driver is None:
            return self._mem_query(namespace, vector, top_k)
        try:
            with self._driver.session(database=settings.neo4j_database) as s:
                rows = s.run(
                    f"CALL db.index.vector.queryNodes('{settings.neo4j_vector_index}', $k, $v) "
                    "YIELD node, score WHERE node.kb_id = $kb "
                    "RETURN node.doc_id AS doc_id, node.title AS title, score",
                    k=top_k, v=vector, kb=namespace,
                )
                return [
                    {"id": r["doc_id"], "score": float(r["score"]),
                     "payload": {"generation_id": r["doc_id"], "title": r["title"]}}
                    for r in rows
                ]
        except Exception as exc:
            log.warning("neo4j query failed (%s); using in-process index", exc)
            return self._mem_query(namespace, vector, top_k)

    def delete_namespace(self, *, namespace, db=None):
        self._mem_delete(namespace)
        if self._driver is None:
            return
        try:
            with self._driver.session(database=settings.neo4j_database) as s:
                s.run("MATCH (d:KbDoc {kb_id: $kb}) DETACH DELETE d", kb=namespace)
        except Exception as exc:
            log.warning("neo4j delete_namespace failed: %s", exc)
