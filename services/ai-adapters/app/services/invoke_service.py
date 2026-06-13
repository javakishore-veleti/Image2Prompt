from __future__ import annotations

import time

from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import Metrics, observe, set_span_attributes

from ..controllers.base import ProviderController
from ..dtos.internal_dtos import InvokeReq, InvokeResp, ProviderInvokeReq


class InvokeService(BaseService):
    """Reusable: dispatches one request to one provider controller and builds a
    structured response. Provider failures never raise — they return an error
    envelope (status='error'), matching the resilient design."""

    def __init__(self, *, registry: dict[str, ProviderController]) -> None:
        super().__init__()
        self.registry = registry

    @observe("InvokeService.dispatch")
    async def dispatch(self, req: InvokeReq) -> InvokeResp:
        controller = self.registry.get(req.provider_key)
        if controller is None:
            return InvokeResp.failure(
                error_code="not_found",
                error_message=f"Unknown provider: {req.provider_key}",
                provider_key=req.provider_key,
                request_id=req.request_id,
                status="error",
            )

        set_span_attributes({"provider.key": req.provider_key, "request.id": req.request_id})
        started = time.perf_counter()
        try:
            presp = await controller.invoke(
                ProviderInvokeReq(
                    request_id=req.request_id,
                    instruction=req.instruction,
                    image_base64=req.image_base64,
                    media_type=req.media_type,
                    config=req.config,
                )
            )
            latency = int((time.perf_counter() - started) * 1000)
            Metrics.counter_add("aiadapters.invoke", 1, {"provider": req.provider_key, "status": "success"})
            Metrics.histogram_record("aiadapters.invoke.duration_ms", latency, {"provider": req.provider_key})
            return InvokeResp(
                provider_key=req.provider_key,
                request_id=req.request_id,
                status="success",
                output_text=presp.output_text,
                raw=presp.raw,
                latency_ms=latency,
            )
        except NotImplementedError as exc:
            latency = int((time.perf_counter() - started) * 1000)
            Metrics.counter_add("aiadapters.invoke", 1, {"provider": req.provider_key, "status": "not_implemented"})
            return InvokeResp(
                provider_key=req.provider_key,
                request_id=req.request_id,
                status="error",
                latency_ms=latency,
                error={"type": "not_implemented", "message": str(exc)},
            )
        except Exception as exc:  # provider/SDK failure (e.g. missing AWS creds)
            latency = int((time.perf_counter() - started) * 1000)
            Metrics.counter_add("aiadapters.invoke", 1, {"provider": req.provider_key, "status": "error"})
            self.log.warning("provider %s failed: %s", req.provider_key, exc)
            return InvokeResp(
                provider_key=req.provider_key,
                request_id=req.request_id,
                status="error",
                latency_ms=latency,
                error={"type": exc.__class__.__name__, "message": str(exc)},
            )
