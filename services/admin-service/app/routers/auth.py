from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.security import create_access_token, verify_password

from ..config import settings
from ..deps import get_db
from ..models import AdminUser
from ..schemas import AdminLogin, TokenResponse

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: AdminLogin, db: Session = Depends(get_db)) -> TokenResponse:
    admin = db.scalar(select(AdminUser).where(AdminUser.email == payload.email))
    if admin is None or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = create_access_token(
        subject=admin.id,
        token_type="admin",
        email=admin.email,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
        extra={"role": admin.role},
    )
    return TokenResponse(access_token=token, email=admin.email, role=admin.role)
