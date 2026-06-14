"""Pluggable vector stores, one per KB tech stack. Every store degrades to an
in-process index on missing SDK/config/error (``ready()`` flags the real backend)."""

from __future__ import annotations

from .base import VectorStore, cosine
from .bedrock import BedrockKbStore
from .chroma import ChromaVectorStore
from .mongodb import MongoVectorStore
from .neo4j_store import Neo4jVectorStore
from .opensearch import OpenSearchStore
from .pinecone_store import PineconeStore
from .sql import SqlVectorStore
from .weaviate_store import WeaviateStore

_REGISTRY = {
    "pgvector": SqlVectorStore,
    "chroma": ChromaVectorStore,
    "bedrock": BedrockKbStore,
    "opensearch": OpenSearchStore,
    "mongodb": MongoVectorStore,
    "neo4j": Neo4jVectorStore,
    "pinecone": PineconeStore,
    "weaviate": WeaviateStore,
}


def build_vector_store(stack: str) -> VectorStore:
    cls = _REGISTRY.get(stack)
    if cls is None:
        return VectorStore()  # unknown stack -> in-process fallback
    return cls()


__all__ = ["VectorStore", "cosine", "build_vector_store"]
