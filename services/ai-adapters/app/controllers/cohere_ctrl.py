"""Cohere provider (real) — Aya Vision via the Cohere v2 chat API."""

from __future__ import annotations

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class CohereController(ProviderController):
    key = "cohere"
    implemented = True

    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        if not self.api_key:
            raise ValueError("COHERE_API_KEY is not configured")
        import cohere

        client = cohere.ClientV2(api_key=self.api_key)
        data_uri = f"data:{req.media_type or 'image/png'};base64,{req.image_base64}"
        model = req.config.get("model", self.model)
        resp = client.chat(
            model=model,
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
        # v2 response: message.content is a list of content blocks with .text
        text = "".join(getattr(b, "text", "") for b in (resp.message.content or []))
        return text.strip(), {"provider": "cohere", "model": model}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
