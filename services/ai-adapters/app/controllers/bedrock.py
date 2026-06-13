from __future__ import annotations

import json

import anyio

from .base import InvokeResult, ProviderController


class BedrockController(ProviderController):
    """AWS Bedrock (Claude) — mirrors the original Whizlabs lab payload.

    Calls ``bedrock-runtime.invoke_model`` with the Anthropic messages format and
    an image block. boto3 is synchronous, so the call is offloaded to a thread.
    """

    key = "bedrock"
    implemented = True

    def __init__(self, *, region: str, model_id: str) -> None:
        self.region = region
        self.model_id = model_id

    def _invoke_sync(self, instruction: str, image_base64: str, media_type: str, config: dict) -> dict:
        import boto3  # imported lazily so the service starts without AWS configured

        client = boto3.client("bedrock-runtime", region_name=config.get("region", self.region))
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.get("max_tokens", 300),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                    ],
                }
            ],
        }
        response = client.invoke_model(
            modelId=config.get("model_id", self.model_id), body=json.dumps(body)
        )
        return json.loads(response["body"].read())

    async def invoke(
        self, *, request_id: str, instruction: str, image_base64: str, media_type: str, config: dict
    ) -> InvokeResult:
        response_body = await anyio.to_thread.run_sync(
            self._invoke_sync, instruction, image_base64, media_type, config
        )
        output_text = response_body["content"][0]["text"]
        return InvokeResult(output_text=output_text, raw=response_body)
