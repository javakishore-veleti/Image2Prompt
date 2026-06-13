"""Microsoft provider (real) — Azure OpenAI (vision) via the openai SDK's
AzureOpenAI client."""

from __future__ import annotations

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class MicrosoftController(ProviderController):
    key = "microsoft"
    implemented = True

    def __init__(self, *, endpoint: str, api_key: str, api_version: str, deployment: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.deployment = deployment

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        if not self.endpoint or not self.api_key:
            raise ValueError("AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY not configured")
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=self.endpoint, api_key=self.api_key, api_version=self.api_version
        )
        data_uri = f"data:{req.media_type or 'image/png'};base64,{req.image_base64}"
        deployment = req.config.get("deployment", self.deployment)
        resp = client.chat.completions.create(
            model=deployment,
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
        return (resp.choices[0].message.content or "").strip(), {"provider": "microsoft", "deployment": deployment}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
