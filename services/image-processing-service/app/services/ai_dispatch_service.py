from __future__ import annotations

from image2prompt_shared.http_client import post_json
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings
from ..dtos.internal_dtos import DispatchReq, DispatchResp


class AiDispatchService(BaseService):
    """Calls ai-adapters /invoke for one provider. Transport failures return an
    error envelope (never raise) so one provider can't fail the whole request."""

    @observe("AiDispatchService.invoke")
    async def invoke(self, req: DispatchReq) -> DispatchResp:
        try:
            payload = await post_json(
                f"{settings.ai_adapters_url}/invoke",
                json={
                    "provider_key": req.provider_key,
                    "request_id": req.request_id,
                    "instruction": req.instruction,
                    "image_base64": req.image_base64,
                    "media_type": req.media_type,
                    "config": req.config,
                },
            )
            return DispatchResp(payload=payload)
        except Exception as exc:
            return DispatchResp.failure(
                error_code="upstream_error",
                error_message=str(exc),
                payload={"status": "error", "error": {"type": exc.__class__.__name__, "message": str(exc)}},
            )
