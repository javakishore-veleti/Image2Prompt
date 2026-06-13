from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..models import Customer, CustomerPreference
from ..schemas import CustomerOut, PreferenceOut, PreferenceUpdate

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("", response_model=CustomerOut)
def get_me(principal: Principal = Depends(current_customer), db: Session = Depends(get_db)):
    customer = db.get(Customer, principal.id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def _get_or_create_prefs(db: Session, customer_id: str) -> CustomerPreference:
    prefs = db.scalar(
        select(CustomerPreference).where(CustomerPreference.customer_id == customer_id)
    )
    if prefs is None:
        prefs = CustomerPreference(customer_id=customer_id, storage_backend="local")
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("/preferences", response_model=PreferenceOut)
def get_preferences(
    principal: Principal = Depends(current_customer), db: Session = Depends(get_db)
):
    return _get_or_create_prefs(db, principal.id)


@router.put("/preferences", response_model=PreferenceOut)
def update_preferences(
    payload: PreferenceUpdate,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
):
    prefs = _get_or_create_prefs(db, principal.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return prefs
