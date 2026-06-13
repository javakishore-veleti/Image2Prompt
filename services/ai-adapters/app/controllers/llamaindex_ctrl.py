"""LlamaIndex provider (real) — a multimodal ChatMessage (TextBlock + ImageBlock)
sent through the BedrockConverse LLM. SDK imported lazily; blocking call offloaded
to a thread."""

from __future__ import annotations

import base64

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class LlamaIndexController(ProviderController):
    key = "llamaindex"
    implemented = True

    def __init__(self, *, region: str, model_id: str) -> None:
        self.region = region
        self.model_id = model_id

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        from llama_index.core.llms import ChatMessage, ImageBlock, TextBlock
        from llama_index.llms.bedrock_converse import BedrockConverse

        llm = BedrockConverse(
            model=req.config.get("model_id", self.model_id),
            region_name=req.config.get("region", self.region),
        )
        message = ChatMessage(
            role="user",
            blocks=[
                TextBlock(text=req.instruction),
                ImageBlock(
                    image=base64.b64decode(req.image_base64),
                    image_mimetype=req.media_type or "image/png",
                ),
            ],
        )
        response = llm.chat([message])
        text = str(getattr(response, "message", response)).strip()
        # ChatResponse.message.content holds the text; fall back to str(response).
        content = getattr(getattr(response, "message", None), "content", None)
        if content:
            text = str(content).strip()
        return text, {"provider": "llamaindex"}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
