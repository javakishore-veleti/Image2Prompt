from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import get_db
from ..di import get_image_facade
from ..dtos.internal_dtos import StatsReq
from ..facades.interfaces import IImageFacade

# Service-to-service: global processing stats for the admin analytics dashboard.
router = APIRouter(prefix="/internal/stats", tags=["stats-internal"])


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
