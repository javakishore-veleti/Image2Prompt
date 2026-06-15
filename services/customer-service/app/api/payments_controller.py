from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..di import get_payments_facade
from ..dtos.internal_dtos import (
    BillingReq,
    ChargeSubscriptionReq,
    GetPaymentReq,
    SetupIntentReq,
    UpdatePaymentReq,
)
from ..facades.interfaces import IPaymentsFacade
from ..schemas import PaymentSettingsOut, PaymentSettingsUpdate

router = APIRouter(prefix="/me", tags=["payments"])


@router.get("/payment-settings")
def get_payment_settings(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IPaymentsFacade = Depends(get_payments_facade),
):
    resp = ensure_ok(facade.get_settings(GetPaymentReq(db=db, customer_id=principal.id)))
    return {
        "customer_id": principal.id,
        "data": resp.settings.data if resp.settings else {},
        "stripe_configured": resp.configured,
        "stripe_customer_id": resp.stripe_customer_id,
    }


@router.put("/payment-settings", response_model=PaymentSettingsOut)
def update_payment_settings(
    payload: PaymentSettingsUpdate,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IPaymentsFacade = Depends(get_payments_facade),
):
    resp = ensure_ok(
        facade.update_settings(UpdatePaymentReq(db=db, customer_id=principal.id, data=payload.data))
    )
    return resp.settings


@router.post("/payment-settings/setup-intent")
def create_setup_intent(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IPaymentsFacade = Depends(get_payments_facade),
):
    resp = ensure_ok(facade.create_setup_intent(SetupIntentReq(db=db, customer_id=principal.id)))
    return {"configured": resp.configured, "client_secret": resp.client_secret}


@router.get("/billing")
def get_billing(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IPaymentsFacade = Depends(get_payments_facade),
):
    resp = ensure_ok(facade.get_billing(BillingReq(db=db, customer_id=principal.id)))
    return {
        "customer_id": principal.id,
        "configured": resp.configured,
        "receipts": resp.receipts,
        "balance_due": resp.balance_due,
        "currency": resp.currency,
        "subscription": resp.subscription,
    }


@router.post("/billing/invoice")
def charge_subscription(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IPaymentsFacade = Depends(get_payments_facade),
):
    """Generate a Stripe invoice for the current month's KB subscription charges."""
    resp = ensure_ok(facade.charge_subscription(ChargeSubscriptionReq(db=db, customer_id=principal.id)))
    return {
        "configured": resp.configured,
        "invoice_id": resp.invoice_id,
        "hosted_invoice_url": resp.hosted_invoice_url,
        "amount": resp.amount,
        "currency": resp.currency,
        "status": resp.status,
        "line_items": resp.line_items,
    }
