"""Mistral provider (real) — Pixtral vision via the mistralai SDK."""

from __future__ import annotations

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class MistralController(ProviderController):
    key = "mistral"
    implemented = True

    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY is not configured")
        from mistralai import Mistral

        client = Mistral(api_key=self.api_key)
        data_uri = f"data:{req.media_type or 'image/png'};base64,{req.image_base64}"
        model = req.config.get("model", self.model)
        resp = client.chat.complete(
            model=model,
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": req.instruction},
                        {"type": "image_url", "image_url": data_uri},
                    ],
                }
            ],
        )
        return (resp.choices[0].message.content or "").strip(), {"provider": "mistral", "model": model}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
