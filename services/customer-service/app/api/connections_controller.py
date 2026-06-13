from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..config import settings
from ..deps import current_customer, get_db
from ..di import get_connections_facade
from ..dtos.internal_dtos import (
    ConnectReq,
    DisconnectReq,
    GoogleAuthorizeReq,
    GoogleCallbackReq,
    ListConnectionsReq,
    ListFilesReq,
)
from ..facades.interfaces import IConnectionsFacade
from ..schemas import ConnectionOut, ConnectRequest, FileOut

router = APIRouter(prefix="/me/connections", tags=["connections"])


@router.post("/google/authorize")
def google_authorize(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    resp = ensure_ok(facade.google_authorize(GoogleAuthorizeReq(db=db, customer_id=principal.id)))
    return {"authorize_url": resp.authorize_url}


@router.get("/google/callback")
def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    # Public browser redirect from Google. Identity comes from the signed state.
    resp = facade.google_callback(GoogleCallbackReq(db=db, code=code, state=state))
    status = "connected" if resp.success else "error"
    return RedirectResponse(url=f"{settings.google_oauth_success_redirect}?google={status}", status_code=302)


@router.get("", response_model=list[ConnectionOut])
def list_connections(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    return ensure_ok(facade.list_connections(ListConnectionsReq(db=db, customer_id=principal.id))).connections


@router.post("", response_model=ConnectionOut, status_code=201)
def connect(
    payload: ConnectRequest,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    return ensure_ok(
        facade.connect(ConnectReq(db=db, customer_id=principal.id, provider=payload.provider))
    ).connection


@router.delete("/{connection_id}", status_code=204)
def disconnect(
    connection_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    ensure_ok(
        facade.disconnect(DisconnectReq(db=db, customer_id=principal.id, connection_id=connection_id))
    )


@router.get("/{connection_id}/files", response_model=list[FileOut])
def list_files(
    connection_id: str,
    search: str | None = Query(default=None),
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IConnectionsFacade = Depends(get_connections_facade),
):
    resp = ensure_ok(
        facade.list_files(
            ListFilesReq(db=db, customer_id=principal.id, connection_id=connection_id, search=search)
        )
    )
    return [FileOut(id=f.id, name=f.name, mime_type=f.mime_type, size=f.size) for f in resp.files]
