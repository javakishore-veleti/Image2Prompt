"""Google provider (real) — google-genai (Gemini) multimodal generate_content."""

from __future__ import annotations

import base64

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class GoogleController(ProviderController):
    key = "google"
    implemented = True

    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not configured")
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        model = req.config.get("model", self.model)
        resp = client.models.generate_content(
            model=model,
            contents=[
                req.instruction,
                types.Part.from_bytes(
                    data=base64.b64decode(req.image_base64),
                    mime_type=req.media_type or "image/png",
                ),
            ],
        )
        return (resp.text or "").strip(), {"provider": "google", "model": model}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
