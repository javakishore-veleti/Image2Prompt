from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import get_db
from ..di import get_internal_facade
from ..dtos.internal_dtos import GetByIdReq, GetPrefsReq, SearchCustomersReq
from ..facades.interfaces import IInternalFacade
from ..schemas import CustomerOut, PreferenceOut

router = APIRouter(prefix="/internal/customers", tags=["customers-internal"])


@router.get("", response_model=list[CustomerOut])
def list_customers(
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    facade: IInternalFacade = Depends(get_internal_facade),
):
    resp = ensure_ok(
        facade.search_customers(SearchCustomersReq(db=db, search=search, limit=limit, offset=offset))
    )
    return resp.customers


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    facade: IInternalFacade = Depends(get_internal_facade),
):
    resp = ensure_ok(facade.get_customer(GetByIdReq(db=db, customer_id=customer_id)))
    return resp.customer


@router.get("/{customer_id}/preferences", response_model=PreferenceOut)
def get_preferences(
    customer_id: str,
    db: Session = Depends(get_db),
    facade: IInternalFacade = Depends(get_internal_facade),
):
    resp = ensure_ok(facade.get_preferences(GetPrefsReq(db=db, customer_id=customer_id)))
    return resp.preference
