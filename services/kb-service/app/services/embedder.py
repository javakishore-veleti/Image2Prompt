"""Text embedders. Amazon Titan on Bedrock by default; degrades to a deterministic
local hashing embedder when boto3/credentials are unavailable, so dev and tests
produce meaningful cosine similarity without any cloud dependency."""

from __future__ import annotations

import hashlib
import math
import re

from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings

_TOKEN = re.compile(r"[a-z0-9]+")


class Embedder(BaseService):
    dim: int = 256

    def embed(self, text: str) -> list[float]:  # pragma: no cover - interface
        raise NotImplementedError


class MockEmbedder(Embedder):
    """Hashing vectorizer: token -> bucket, L2-normalized. Overlapping text yields
    high cosine similarity, which is what KB search needs in dev/tests."""

    def __init__(self, dim: int = 256) -> None:
        super().__init__()
        self.dim = dim

    @observe("MockEmbedder.embed")
    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _TOKEN.findall((text or "").lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else vec


class BedrockTitanEmbedder(Embedder):
    """Real Amazon Titan embeddings via Bedrock Runtime; falls back to MockEmbedder
    on any error (missing boto3/creds/model)."""

    def __init__(self, *, region: str, model_id: str, fallback: Embedder) -> None:
        super().__init__()
        self.region = region
        self.model_id = model_id
        self._fallback = fallback
        self.dim = fallback.dim

    @observe("BedrockTitanEmbedder.embed")
    def embed(self, text: str) -> list[float]:
        try:
            import json

            import boto3

            client = boto3.client("bedrock-runtime", region_name=self.region)
            resp = client.invoke_model(
                modelId=self.model_id, body=json.dumps({"inputText": text or ""})
            )
            data = json.loads(resp["body"].read())
            emb = data.get("embedding") or []
            if emb:
                self.dim = len(emb)
                return [float(x) for x in emb]
        except Exception as exc:  # never break ingestion/query on embedding issues
            self.log.warning("Titan embed failed (%s); using local embedder", exc)
        return self._fallback.embed(text)


def build_embedder() -> Embedder:
    mock = MockEmbedder(dim=settings.embedding_dim)
    if settings.embedding_backend == "bedrock":
        return BedrockTitanEmbedder(
            region=settings.aws_region, model_id=settings.bedrock_embed_model_id, fallback=mock
        )
    return mock
