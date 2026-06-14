from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import get_db
from ..di import get_image_facade
from ..dtos.internal_dtos import ResolveRequestsReq, StatsReq
from ..facades.interfaces import IImageFacade

# Service-to-service: global processing stats for the admin analytics dashboard.
router = APIRouter(prefix="/internal/stats", tags=["stats-internal"])
# Service-to-service: kb-service resolves generations to ingest into a Project KB.
requests_internal = APIRouter(prefix="/internal/requests", tags=["requests-internal"])


@requests_internal.post("/resolve")
def resolve_requests(
    customer_id: str = Body(...),
    request_ids: list[str] = Body(default_factory=list),
    db: Session = Depends(get_db),
    facade: IImageFacade = Depends(get_image_facade),
):
    resp = ensure_ok(
        facade.resolve_requests(ResolveRequestsReq(db=db, customer_id=customer_id, request_ids=request_ids))
    )
    out = []
    for r in resp.requests:
        prompts = [
            {"provider_key": p.provider_key, "output_text": p.output_text}
            for p in r.providers
            if p.status == "success" and p.output_text
        ]
        out.append(
            {
                "id": r.id,
                "instruction": r.instruction,
                "project_id": r.project_id,
                "file_ref_id": r.file_ref_id,
                "prompts": prompts,
            }
        )
    return out


@router.get("")
def stats(
    days: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
    facade: IImageFacade = Depends(get_image_facade),
):
    resp = ensure_ok(facade.stats(StatsReq(db=db, days=days)))
    return {
        "total_requests": resp.total_requests,
        "by_status": resp.by_status,
        "providers": resp.providers,
        "over_time": resp.over_time,
    }
