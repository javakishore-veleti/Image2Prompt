from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..di import get_payments_facade
from ..dtos.internal_dtos import BillingReq, GetPaymentReq, UpdatePaymentReq
from ..facades.interfaces import IPaymentsFacade
from ..schemas import PaymentSettingsOut, PaymentSettingsUpdate

router = APIRouter(prefix="/me", tags=["payments"])


@router.get("/payment-settings", response_model=PaymentSettingsOut)
def get_payment_settings(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IPaymentsFacade = Depends(get_payments_facade),
):
    resp = ensure_ok(facade.get_settings(GetPaymentReq(db=db, customer_id=principal.id)))
    return resp.settings


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


@router.get("/billing")
def get_billing(
    principal: Principal = Depends(current_customer),
    facade: IPaymentsFacade = Depends(get_payments_facade),
):
    resp = ensure_ok(facade.get_billing(BillingReq(customer_id=principal.id)))
    return {
        "customer_id": principal.id,
        "receipts": resp.receipts,
        "balance_due": resp.balance_due,
        "currency": resp.currency,
    }
