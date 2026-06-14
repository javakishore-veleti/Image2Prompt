"""pgvector stack -> real, persistent SQL-backed store (KbVector table, cosine in
Python). Works on Postgres and SQLite, so it's the dev/test workhorse."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...models import KbVector
from .base import VectorStore, cosine


class SqlVectorStore(VectorStore):
    stack = "pgvector"

    def ready(self) -> bool:
        return True

    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db: Session = None):
        db.execute(delete(KbVector).where(KbVector.kb_id == namespace, KbVector.doc_id == doc_id))
        db.add(KbVector(kb_id=namespace, doc_id=doc_id, vector=vector, payload=payload or {}))
        db.flush()

    def query(self, *, namespace, vector, text="", top_k=5, db: Session = None):
        rows = db.scalars(select(KbVector).where(KbVector.kb_id == namespace)).all()
        scored = [
            {"id": r.doc_id, "score": cosine(vector, r.vector or []), "payload": r.payload or {}}
            for r in rows
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
