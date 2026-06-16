"""VectorStore base + in-process fallback.

Every store implements the same interface and MUST degrade to the in-process
index on any error (missing SDK / config / network), never raising — exactly like
the AI providers. ``ready()`` reflects whether the real external backend is live.

The interface carries both the embedding ``vector`` and the raw ``text``: most
stores rank by vector; managed RAG stores (Bedrock KB) index/retrieve by text.
"""

from __future__ import annotations

import math

from image2prompt_shared.logging_config import get_logger

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
        return False

    # --- in-process fallback (used when the real backend isn't available) ---
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

    def _mem_delete(self, namespace):
        _MEM.pop((self.stack, namespace), None)

    # --- public interface (override the real backend; fall back on error) ---
    def upsert(self, *, namespace, doc_id, vector, text="", payload=None, db=None):
        self._mem_upsert(namespace, doc_id, vector, payload)

    def query(self, *, namespace, vector, text="", top_k=5, db=None):
        return self._mem_query(namespace, vector, top_k)

    def delete_namespace(self, *, namespace, db=None):
        """Remove all vectors for a KB. Called on KB delete so the external store
        doesn't leak data (and keep counting toward billing). Best-effort: errors
        are swallowed after cleaning the in-process fallback."""
        self._mem_delete(namespace)
