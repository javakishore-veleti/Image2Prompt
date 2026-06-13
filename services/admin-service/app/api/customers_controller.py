from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import admin_writer, current_admin, get_db
from ..di import get_customers_facade
from ..dtos.internal_dtos import (
    GetCustomerActivityReq,
    GetCustomerConnectionsReq,
    ProxyCustomersReq,
    UnlockCustomerReq,
)
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


@router.get("/{customer_id}/connections")
async def customer_connections(
    customer_id: str,
    _=Depends(current_admin),
    facade: ICustomersFacade = Depends(get_customers_facade),
):
    resp = ensure_ok(await facade.get_connections(GetCustomerConnectionsReq(customer_id=customer_id)))
    return resp.connections


@router.get("/{customer_id}/activity")
async def customer_activity(
    customer_id: str,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    _=Depends(current_admin),
    facade: ICustomersFacade = Depends(get_customers_facade),
):
    resp = ensure_ok(
        await facade.get_activity(
            GetCustomerActivityReq(customer_id=customer_id, limit=limit, offset=offset)
        )
    )
    return resp.entries


@router.post("/{customer_id}/unlock")
async def unlock_customer(
    customer_id: str,
    principal: Principal = Depends(admin_writer),
    db: Session = Depends(get_db),
    facade: ICustomersFacade = Depends(get_customers_facade),
):
    resp = ensure_ok(
        await facade.unlock_customer(
            UnlockCustomerReq(
                db=db, customer_id=customer_id, actor_id=principal.id, actor_email=principal.email
            )
        )
    )
    return {"message": resp.message}
