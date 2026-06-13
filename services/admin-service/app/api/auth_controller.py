from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import get_db
from ..di import get_auth_facade
from ..dtos.internal_dtos import AdminLoginReq, AdminLogoutReq, AdminRefreshReq
from ..facades.interfaces import IAdminAuthFacade
from ..schemas import AdminLogin, RefreshRequest, TokenResponse

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


def _token_response(resp) -> TokenResponse:
    return TokenResponse(
        access_token=resp.access_token,
        refresh_token=resp.refresh_token,
        email=resp.email,
        role=resp.role,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: AdminLogin,
    db: Session = Depends(get_db),
    facade: IAdminAuthFacade = Depends(get_auth_facade),
) -> TokenResponse:
    return _token_response(
        ensure_ok(facade.login(AdminLoginReq(db=db, email=payload.email, password=payload.password)))
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    facade: IAdminAuthFacade = Depends(get_auth_facade),
) -> TokenResponse:
    return _token_response(
        ensure_ok(facade.refresh(AdminRefreshReq(db=db, refresh_token=payload.refresh_token)))
    )


@router.post("/logout", status_code=204)
def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    facade: IAdminAuthFacade = Depends(get_auth_facade),
):
    ensure_ok(facade.logout(AdminLogoutReq(db=db, refresh_token=payload.refresh_token)))
