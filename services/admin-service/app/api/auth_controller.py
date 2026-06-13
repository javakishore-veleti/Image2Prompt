from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import get_db
from ..di import get_auth_facade
from ..dtos.internal_dtos import AdminLoginReq
from ..facades.interfaces import IAdminAuthFacade
from ..schemas import AdminLogin, TokenResponse

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: AdminLogin,
    db: Session = Depends(get_db),
    facade: IAdminAuthFacade = Depends(get_auth_facade),
) -> TokenResponse:
    resp = ensure_ok(facade.login(AdminLoginReq(db=db, email=payload.email, password=payload.password)))
    return TokenResponse(access_token=resp.access_token, email=resp.email, role=resp.role)
