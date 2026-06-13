"""Anthropic provider (real) — Claude Messages API (vision) via the anthropic SDK."""

from __future__ import annotations

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class AnthropicController(ProviderController):
    key = "anthropic"
    implemented = True

    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        model = req.config.get("model", self.model)
        message = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": req.instruction},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": req.media_type or "image/png",
                                "data": req.image_base64,
                            },
                        },
                    ],
                }
            ],
        )
        text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
        return text.strip(), {"provider": "anthropic", "model": model}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
