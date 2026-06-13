from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.security import (
    create_access_token,
    hash_password,
    verify_password,
)

from ..config import settings
from ..deps import get_db
from ..models import Customer, CustomerPreference
from ..schemas import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["customer-auth"])


def _token_for(customer: Customer) -> str:
    return create_access_token(
        subject=customer.id,
        token_type="customer",
        email=customer.email,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.scalar(select(Customer).where(Customer.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    customer = Customer(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
    )
    db.add(customer)
    db.flush()  # assign id
    # Create default preferences (empty provider list => use admin defaults).
    db.add(CustomerPreference(customer_id=customer.id, storage_backend="local"))
    db.commit()
    db.refresh(customer)
    return TokenResponse(
        access_token=_token_for(customer), customer_id=customer.id, email=customer.email
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    customer = db.scalar(select(Customer).where(Customer.email == payload.email))
    if customer is None or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return TokenResponse(
        access_token=_token_for(customer), customer_id=customer.id, email=customer.email
    )
