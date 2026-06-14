"""Catalog of KB vector-store tech stacks a subscription plan can price/allow.
Shared vocabulary between Subscriptions (admin) and the kb-service."""

from __future__ import annotations

# Keys must match the VectorStore provider keys in kb-service.
TECH_STACKS: list[str] = [
    "bedrock",     # Amazon Bedrock Knowledge Bases
    "opensearch",  # AWS OpenSearch (vector)
    "pgvector",    # PostgreSQL + pgvector
    "mongodb",     # MongoDB Atlas Vector Search
    "weaviate",
    "pinecone",
    "chroma",
    "neo4j",       # neo4j vector index
]

_VALID = set(TECH_STACKS)


def is_valid_stack(stack: str) -> bool:
    return stack in _VALID
