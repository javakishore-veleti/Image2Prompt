from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from image2prompt_shared.api_errors import ensure_ok

from ..deps import current_admin
from ..di import get_customers_facade
from ..dtos.internal_dtos import ProxyCustomersReq
from ..facades.interfaces import ICustomersFacade
from ..schemas import CustomerOut

router = APIRouter(prefix="/admin/customers", tags=["admin-customers"])


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    _=Depends(current_admin),
    facade: ICustomersFacade = Depends(get_customers_facade),
):
    resp = ensure_ok(
        await facade.search_customers(ProxyCustomersReq(search=search, limit=limit, offset=offset))
    )
    return resp.customers
