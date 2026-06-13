from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import get_db
from ..di import get_connections_facade, get_internal_facade
from ..dtos.internal_dtos import (
    CountCustomersReq,
    DownloadFileReq,
    GetByIdReq,
    GetPrefsReq,
    ListConnectionsReq,
    ReencryptTokensReq,
    SearchCustomersReq,
)
from ..facades.interfaces import IConnectionsFacade, IInternalFacade
from ..schemas import ConnectionOut, CustomerOut, PreferenceOut

router = APIRouter(prefix="/internal/customers", tags=["customers-internal"])
# Service-to-service maintenance (trusted network) — triggered by admin-service.
maintenance = APIRouter(prefix="/internal/maintenance", tags=["maintenance-internal"])


@maintenance.post("/reencrypt-tokens")
def reencrypt_tokens(
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    resp = ensure_ok(facade.reencrypt_tokens(ReencryptTokensReq(db=db)))
    return {"reencrypted": resp.count}


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


# Defined before /{customer_id} so "count" isn't captured as an id.
@router.get("/count")
def count_customers(
    db: Session = Depends(get_db),
    facade: IInternalFacade = Depends(get_internal_facade),
):
    return {"count": ensure_ok(facade.count_customers(CountCustomersReq(db=db))).count}


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


@router.get("/{customer_id}/connections", response_model=list[ConnectionOut])
def get_connections(
    customer_id: str,
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    return ensure_ok(
        facade.list_connections(ListConnectionsReq(db=db, customer_id=customer_id))
    ).connections


@router.get("/{customer_id}/connections/{connection_id}/files/{file_id}/content")
def download_connection_file(
    customer_id: str,
    connection_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    resp = ensure_ok(
        facade.download_file(
            DownloadFileReq(
                db=db, customer_id=customer_id, connection_id=connection_id, file_id=file_id
            )
        )
    )
    return Response(content=resp.content, media_type=resp.content_type)
