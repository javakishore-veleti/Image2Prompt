from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .registry import REGISTRY
from .schemas import InvokeRequest, InvokeResponse, ProviderInfo

app = FastAPI(title="Image2Prompt AI Adapters")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "ai-adapters"}


@app.get("/providers", response_model=list[ProviderInfo], tags=["providers"])
def list_providers():
    return [ProviderInfo(key=k, implemented=c.implemented) for k, c in REGISTRY.items()]


@app.post("/invoke", response_model=InvokeResponse, tags=["invoke"])
async def invoke(req: InvokeRequest) -> InvokeResponse:
    controller = REGISTRY.get(req.provider_key)
    if controller is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {req.provider_key}")

    started = time.perf_counter()
    try:
        result = await controller.invoke(
            request_id=req.request_id,
            instruction=req.instruction,
            image_base64=req.image_base64,
            media_type=req.media_type,
            config=req.config,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return InvokeResponse(
            provider_key=req.provider_key,
            request_id=req.request_id,
            status="success",
            output_text=result.output_text,
            raw=result.raw,
            latency_ms=latency_ms,
        )
    except NotImplementedError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return InvokeResponse(
            provider_key=req.provider_key,
            request_id=req.request_id,
            status="error",
            latency_ms=latency_ms,
            error={"type": "not_implemented", "message": str(exc)},
        )
    except Exception as exc:  # provider/SDK failure (e.g. missing AWS creds)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return InvokeResponse(
            provider_key=req.provider_key,
            request_id=req.request_id,
            status="error",
            latency_ms=latency_ms,
            error={"type": exc.__class__.__name__, "message": str(exc)},
        )
