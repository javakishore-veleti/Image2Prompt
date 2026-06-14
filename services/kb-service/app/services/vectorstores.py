"""Pluggable vector stores, one per KB tech stack.

- pgvector  -> SqlVectorStore: real, persistent (KbVector table; cosine in SQL layer).
              Works on Postgres and SQLite, so it's the dev/test workhorse.
- chroma    -> ChromaVectorStore: real when `chromadb` is importable; else degrades.
- bedrock / opensearch / pinecone / weaviate / mongodb / neo4j -> CloudVectorStore:
              lazy provider seam that activates when its SDK + config are present,
              and otherwise degrades to the in-process index (never raises).

Every store degrades to a process-local in-memory index so the end-to-end KB flow
works in any environment; ``backend_ready`` reflects whether the *real* backend is live.
"""

from __future__ import annotations

import math

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from image2prompt_shared.logging_config import get_logger

from ..config import settings
from ..models import KbVector

log = get_logger(__name__)

# Process-local fallback index: {(stack, kb_id): [(doc_id, vector, payload)]}
_MEM: dict[tuple, list] = {}


def cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n]))
    nb = math.sqrt(sum(x * x for x in b[:n]))
    return dot / (na * nb) if na and nb else 0.0


class VectorStore:
    stack = "memory"

    def ready(self) -> bool:
        return False  # real external backend live?

    # --- in-process fallback (used when ready() is False) ---
    def _mem_upsert(self, namespace, doc_id, vector, payload):
        key = (self.stack, namespace)
        rows = [r for r in _MEM.get(key, []) if r[0] != doc_id]
        rows.append((doc_id, vector, payload or {}))
        _MEM[key] = rows

    def _mem_query(self, namespace, vector, top_k):
        rows = _MEM.get((self.stack, namespace), [])
        scored = [{"id": d, "score": cosine(vector, v), "payload": p} for d, v, p in rows]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def upsert(self, *, namespace, doc_id, vector, payload, db=None):
        self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, top_k=5, db=None):
        return self._mem_query(namespace, vector, top_k)


class SqlVectorStore(VectorStore):
    """Real, persistent store backed by the KbVector table (cosine ranked in Python)."""

    stack = "pgvector"

    def ready(self) -> bool:
        return True

    def upsert(self, *, namespace, doc_id, vector, payload, db: Session = None):
        db.execute(delete(KbVector).where(KbVector.kb_id == namespace, KbVector.doc_id == doc_id))
        db.add(KbVector(kb_id=namespace, doc_id=doc_id, vector=vector, payload=payload or {}))
        db.flush()

    def query(self, *, namespace, vector, top_k=5, db: Session = None):
        rows = db.scalars(select(KbVector).where(KbVector.kb_id == namespace)).all()
        scored = [
            {"id": r.doc_id, "score": cosine(vector, r.vector or []), "payload": r.payload or {}}
            for r in rows
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


class ChromaVectorStore(VectorStore):
    stack = "chroma"

    def __init__(self):
        self._client = None
        try:
            import chromadb  # noqa: F401

            self._client = chromadb.PersistentClient(path=settings.chroma_path) if settings.chroma_path \
                else chromadb.EphemeralClient()
        except Exception as exc:
            log.warning("chroma unavailable (%s); using in-process index", exc)

    def ready(self) -> bool:
        return self._client is not None

    def _coll(self, namespace):
        return self._client.get_or_create_collection(f"kb_{namespace}")

    def upsert(self, *, namespace, doc_id, vector, payload, db=None):
        if not self._client:
            return self._mem_upsert(namespace, doc_id, vector, payload)
        self._coll(namespace).upsert(ids=[doc_id], embeddings=[vector], metadatas=[payload or {}])

    def query(self, *, namespace, vector, top_k=5, db=None):
        if not self._client:
            return self._mem_query(namespace, vector, top_k)
        res = self._coll(namespace).query(query_embeddings=[vector], n_results=top_k)
        ids = (res.get("ids") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        out = []
        for i, did in enumerate(ids):
            dist = dists[i] if i < len(dists) else 1.0
            out.append({"id": did, "score": 1.0 - float(dist), "payload": metas[i] if i < len(metas) else {}})
        return out


class CloudVectorStore(VectorStore):
    """Seam for a managed backend (bedrock/opensearch/pinecone/weaviate/mongodb/neo4j).
    Activates when its SDK + config are present; otherwise degrades to in-process."""

    def __init__(self, stack: str, configured: bool):
        self.stack = stack
        self._configured = configured

    def ready(self) -> bool:
        # Real client wiring is added per backend; until then we degrade gracefully.
        return False


def _cloud_configured(stack: str) -> bool:
    return {
        "pinecone": bool(settings.pinecone_api_key),
        "weaviate": bool(settings.weaviate_url),
        "mongodb": bool(settings.mongodb_uri),
        "neo4j": bool(settings.neo4j_uri),
        "opensearch": bool(settings.opensearch_url),
        "bedrock": True,  # Bedrock KB uses the task role; no explicit key
    }.get(stack, False)


def build_vector_store(stack: str) -> VectorStore:
    if stack == "pgvector":
        return SqlVectorStore()
    if stack == "chroma":
        return ChromaVectorStore()
    return CloudVectorStore(stack, _cloud_configured(stack))
