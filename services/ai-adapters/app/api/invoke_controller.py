from __future__ import annotations

from fastapi import APIRouter, Depends

from image2prompt_shared.api_errors import ensure_ok

from ..di import get_invoke_facade
from ..dtos.internal_dtos import InvokeReq, ListProvidersReq
from ..facades.interfaces import IInvokeFacade
from ..schemas import InvokeRequest, InvokeResponse, ProviderInfo

router = APIRouter(tags=["invoke"])


@router.get("/providers", response_model=list[ProviderInfo])
def list_providers(facade: IInvokeFacade = Depends(get_invoke_facade)):
    resp = facade.list_providers(ListProvidersReq())
    return [ProviderInfo(key=p.key, implemented=p.implemented) for p in resp.providers]


@router.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest, facade: IInvokeFacade = Depends(get_invoke_facade)):
    resp = ensure_ok(
        await facade.invoke(
            InvokeReq(
                provider_key=req.provider_key,
                request_id=req.request_id,
                instruction=req.instruction,
                image_base64=req.image_base64,
                media_type=req.media_type,
                config=req.config,
            )
        )
    )
    return InvokeResponse(
        provider_key=resp.provider_key,
        request_id=resp.request_id,
        status=resp.status,
        output_text=resp.output_text,
        raw=resp.raw,
        latency_ms=resp.latency_ms,
        error=resp.error,
    )
