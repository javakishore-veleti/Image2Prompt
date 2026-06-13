from __future__ import annotations

import json

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class BedrockController(ProviderController):
    """AWS Bedrock (Claude) — mirrors the original Whizlabs lab payload."""

    key = "bedrock"
    implemented = True

    def __init__(self, *, region: str, model_id: str) -> None:
        self.region = region
        self.model_id = model_id

    def _invoke_sync(self, req: ProviderInvokeReq) -> dict:
        import boto3  # imported lazily so the service starts without AWS configured

        client = boto3.client("bedrock-runtime", region_name=req.config.get("region", self.region))
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": req.config.get("max_tokens", 300),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": req.instruction},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": req.media_type,
                                "data": req.image_base64,
                            },
                        },
                    ],
                }
            ],
        }
        response = client.invoke_model(
            modelId=req.config.get("model_id", self.model_id), body=json.dumps(body)
        )
        return json.loads(response["body"].read())

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        response_body = await anyio.to_thread.run_sync(self._invoke_sync, req)
        output_text = response_body["content"][0]["text"]
        return ProviderInvokeResp(output_text=output_text, raw=response_body)
