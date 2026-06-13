"""OpenAI provider (real) — Chat Completions (vision) via the openai SDK."""

from __future__ import annotations

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class OpenAIController(ProviderController):
    key = "openai"
    implemented = True

    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        data_uri = f"data:{req.media_type or 'image/png'};base64,{req.image_base64}"
        model = req.config.get("model", self.model)
        resp = client.chat.completions.create(
            model=model,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": req.instruction},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
        )
        return (resp.choices[0].message.content or "").strip(), {"provider": "openai", "model": model}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
