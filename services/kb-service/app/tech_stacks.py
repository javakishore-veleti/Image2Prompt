"""KB vector-store tech stacks (must match admin-service Subscriptions catalog)."""

from __future__ import annotations

TECH_STACKS: list[str] = [
    "bedrock",
    "opensearch",
    "pgvector",
    "mongodb",
    "weaviate",
    "pinecone",
    "chroma",
    "neo4j",
]

_VALID = set(TECH_STACKS)


def is_valid_stack(stack: str) -> bool:
    return stack in _VALID
