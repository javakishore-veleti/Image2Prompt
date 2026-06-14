from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class KbSettings(ServiceSettings):
    service_name: str = "kb-service"
    db_schema: str = "img2pmpt_kb"

    # Embeddings (Amazon Titan on Bedrock by default; degrades to a deterministic
    # local embedder when boto3/credentials are absent so dev/tests still work).
    embedding_backend: str = "bedrock"  # bedrock | mock
    aws_region: str = "us-east-1"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"
    embedding_dim: int = 256  # used by the mock embedder

    # Fail closed: require a customer's subscription to allow a KB's tech stack.
    # Disable in local/dev/tests where admin-service isn't reachable.
    kb_require_subscription: bool = True

    # Per-backend connection settings (only used when that stack is selected;
    # all degrade gracefully to an in-process index if unset/unavailable).
    pinecone_api_key: str = ""
    weaviate_url: str = ""
    weaviate_api_key: str = ""
    mongodb_uri: str = ""
    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""
    opensearch_url: str = ""
    chroma_path: str = ""  # local persistent dir; empty => ephemeral


settings = KbSettings()
