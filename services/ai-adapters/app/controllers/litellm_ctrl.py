"""LiteLLM provider — delegates to the img2pmpt-caf-routers library."""

from __future__ import annotations

import anyio

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class LiteLLMController(ProviderController):
    key = "litellm"
    implemented = True

    def _run_sync(self, req: ProviderInvokeReq) -> tuple[str, dict]:
        from img2pmpt_caf_routers import RouteReq, get_router_client

        resp = get_router_client().route(
            RouteReq(
                router="litellm",
                instruction=req.instruction,
                image_base64=req.image_base64,
                media_type=req.media_type,
                model=req.config.get("model"),
            )
        )
        if not resp.success:
            raise RuntimeError(resp.error_message or resp.error_code or "litellm failed")
        return resp.output_text, {"provider": "litellm", "model": resp.model, **resp.raw}

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        output_text, raw = await anyio.to_thread.run_sync(self._run_sync, req)
        return ProviderInvokeResp(output_text=output_text, raw=raw)
