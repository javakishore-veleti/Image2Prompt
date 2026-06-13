"""Ollama provider (real, local) — vision models (e.g. llava) via Ollama's
OpenAI-compatible endpoint. No API key; if Ollama isn't reachable the call fails
into the standard error envelope."""

from __future__ import annotations

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class OllamaController(ProviderController):
    key = "ollama"
    implemented = True

    def __init__(self, *, base_url: str, model: str) -> None:
        self.base_url = base_url
        self.model = model

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        from openai import OpenAI

        client = OpenAI(base_url=self.base_url, api_key="ollama")  # key ignored locally
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
        return (resp.choices[0].message.content or "").strip(), {"provider": "ollama", "model": model}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
