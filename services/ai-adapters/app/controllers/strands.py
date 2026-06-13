"""AWS Strands Agents provider (real).

Strands is an agent framework, not a model vendor — it runs on an underlying
model. Here it uses the Bedrock model provider (Claude) and is invoked with a
multimodal message (instruction text + the uploaded image). The SDK is imported
lazily and the blocking agent call is offloaded to a worker thread.
"""

from __future__ import annotations

import base64

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController

# Bedrock image "format" values, derived from the upload's media type.
_FORMAT_MAP = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}

_SYSTEM_PROMPT = (
    "You are an expert at reverse-engineering text-to-image prompts. Given an "
    "image, produce a single, detailed prompt that could recreate it — covering "
    "subject, composition, style, lighting, lens/camera, and mood."
)


def _extract_text(result) -> str:
    # Strands AgentResult stringifies to the assistant's text response.
    text = str(result).strip()
    if text:
        return text
    message = getattr(result, "message", None)
    if isinstance(message, dict):
        parts = [c.get("text", "") for c in message.get("content", []) if isinstance(c, dict)]
        return "".join(parts).strip()
    return ""


class StrandsController(ProviderController):
    key = "strands"
    implemented = True

    def __init__(self, *, region: str, model_id: str) -> None:
        self.region = region
        self.model_id = model_id

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        from strands import Agent  # lazy: only needed when Strands is dispatched
        from strands.models import BedrockModel

        image_bytes = base64.b64decode(req.image_base64)
        fmt = _FORMAT_MAP.get((req.media_type or "image/png").split("/")[-1].lower(), "png")

        model = BedrockModel(
            model_id=req.config.get("model_id", self.model_id),
            region_name=req.config.get("region", self.region),
        )
        agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)
        result = agent(
            [
                {"text": req.instruction},
                {"image": {"format": fmt, "source": {"bytes": image_bytes}}},
            ]
        )
        raw = {
            "provider": "strands",
            "model_id": req.config.get("model_id", self.model_id),
            "stop_reason": getattr(result, "stop_reason", None),
        }
        return _extract_text(result), raw

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
