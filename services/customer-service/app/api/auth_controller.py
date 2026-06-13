from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import get_db
from ..di import get_auth_facade
from ..dtos.internal_dtos import LoginReq, RefreshReq, SignupReq
from ..facades.interfaces import IAuthFacade
from ..schemas import LoginRequest, RefreshRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["customer-auth"])


def _token_response(resp) -> TokenResponse:
    return TokenResponse(
        access_token=resp.access_token,
        refresh_token=resp.refresh_token,
        customer_id=resp.customer_id,
        email=resp.email,
    )


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(
    payload: SignupRequest,
    db: Session = Depends(get_db),
    facade: IAuthFacade = Depends(get_auth_facade),
) -> TokenResponse:
    return _token_response(
        ensure_ok(
            facade.signup(
                SignupReq(db=db, email=payload.email, password=payload.password, name=payload.name)
            )
        )
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    facade: IAuthFacade = Depends(get_auth_facade),
) -> TokenResponse:
    return _token_response(
        ensure_ok(facade.login(LoginReq(db=db, email=payload.email, password=payload.password)))
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    facade: IAuthFacade = Depends(get_auth_facade),
) -> TokenResponse:
    return _token_response(
        ensure_ok(facade.refresh(RefreshReq(db=db, refresh_token=payload.refresh_token)))
    )
