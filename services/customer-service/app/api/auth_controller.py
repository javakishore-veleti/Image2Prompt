from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..di import get_auth_facade
from ..dtos.internal_dtos import (
    LoginReq,
    LogoutReq,
    RefreshReq,
    RequestPasswordResetReq,
    ResetPasswordReq,
    SendVerificationReq,
    SignupReq,
    VerifyEmailReq,
)
from ..facades.interfaces import IAuthFacade
from ..schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    VerifyEmailRequest,
)

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


@router.post("/logout", status_code=204)
def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    facade: IAuthFacade = Depends(get_auth_facade),
):
    ensure_ok(facade.logout(LogoutReq(db=db, refresh_token=payload.refresh_token)))


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    facade: IAuthFacade = Depends(get_auth_facade),
) -> MessageResponse:
    resp = ensure_ok(facade.request_password_reset(RequestPasswordResetReq(db=db, email=payload.email)))
    return MessageResponse(message=resp.message)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    facade: IAuthFacade = Depends(get_auth_facade),
) -> MessageResponse:
    resp = ensure_ok(
        facade.reset_password(ResetPasswordReq(db=db, token=payload.token, new_password=payload.new_password))
    )
    return MessageResponse(message=resp.message)


@router.post("/send-verification", response_model=MessageResponse)
def send_verification(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IAuthFacade = Depends(get_auth_facade),
) -> MessageResponse:
    resp = ensure_ok(facade.send_verification_email(SendVerificationReq(db=db, customer_id=principal.id)))
    return MessageResponse(message=resp.message)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
    facade: IAuthFacade = Depends(get_auth_facade),
) -> MessageResponse:
    resp = ensure_ok(facade.verify_email(VerifyEmailReq(db=db, token=payload.token)))
    return MessageResponse(message=resp.message)
