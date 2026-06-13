from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import current_admin, get_db
from ..di import get_analytics_facade
from ..dtos.internal_dtos import GetAnalyticsReq
from ..facades.interfaces import IAnalyticsFacade

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])


@router.get("")
async def analytics(
    days: int = Query(default=14, ge=1, le=90),
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: IAnalyticsFacade = Depends(get_analytics_facade),
):
    resp = ensure_ok(await facade.get_analytics(GetAnalyticsReq(db=db, days=days)))
    return {
        "customers": resp.customers,
        "providers_total": resp.providers_total,
        "providers_enabled": resp.providers_enabled,
        "image_stats": resp.image_stats,
        "csp": {
            "total": resp.csp_total,
            "distinct": resp.csp_distinct,
            "top_directive": resp.csp_top_directive,
        },
    }
