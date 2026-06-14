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

    # Chroma (real, local).
    chroma_path: str = ""  # local persistent dir; empty => ephemeral

    # AWS Bedrock Knowledge Bases (managed RAG over S3). ready() needs id + bucket.
    bedrock_kb_id: str = ""
    bedrock_kb_s3_bucket: str = ""
    bedrock_kb_data_source_id: str = ""
    bedrock_kb_prefix: str = "kb/"  # S3 key prefix for ingested docs

    # AWS OpenSearch (k-NN).
    opensearch_url: str = ""
    opensearch_user: str = ""
    opensearch_password: str = ""
    opensearch_index_prefix: str = "img2pmpt-kb"

    # MongoDB Atlas Vector Search (index must be pre-created in Atlas).
    mongodb_uri: str = ""
    mongodb_db: str = "img2pmpt"
    mongodb_collection: str = "kb_vectors"
    mongodb_vector_index: str = "kb_vector_index"

    # neo4j vector index.
    neo4j_uri: str = ""
    neo4j_user: str = ""
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
    neo4j_vector_index: str = "kb_vector_index"

    # Pinecone serverless.
    pinecone_api_key: str = ""
    pinecone_index: str = "img2pmpt-kb"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # Weaviate Cloud.
    weaviate_url: str = ""
    weaviate_api_key: str = ""
    weaviate_collection: str = "Img2pmptKb"


settings = KbSettings()
