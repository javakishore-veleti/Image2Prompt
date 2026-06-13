from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..models import PaymentSettings
from ..schemas import PaymentSettingsOut, PaymentSettingsUpdate

# Payment Settings + Billing & Receipts. Stripe is stubbed for the slice:
# settings are stored as JSON and billing returns an empty receipt list.
router = APIRouter(prefix="/me", tags=["payments"])


def _get_or_create(db: Session, customer_id: str) -> PaymentSettings:
    ps = db.scalar(select(PaymentSettings).where(PaymentSettings.customer_id == customer_id))
    if ps is None:
        ps = PaymentSettings(customer_id=customer_id, data={})
        db.add(ps)
        db.commit()
        db.refresh(ps)
    return ps


@router.get("/payment-settings", response_model=PaymentSettingsOut)
def get_payment_settings(
    principal: Principal = Depends(current_customer), db: Session = Depends(get_db)
):
    return _get_or_create(db, principal.id)


@router.put("/payment-settings", response_model=PaymentSettingsOut)
def update_payment_settings(
    payload: PaymentSettingsUpdate,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
):
    ps = _get_or_create(db, principal.id)
    ps.data = payload.data
    db.commit()
    db.refresh(ps)
    return ps


@router.get("/billing")
def get_billing(principal: Principal = Depends(current_customer)):
    # Stub: real billing/receipts come from Stripe in a later pass.
    return {"customer_id": principal.id, "receipts": [], "balance_due": 0, "currency": "USD"}
