from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.payment_dao import PaymentDao
from ..dtos.internal_dtos import (
    BillingReq,
    BillingResp,
    GetPaymentReq,
    PaymentResp,
    UpdatePaymentReq,
)
from .interfaces import IPaymentsFacade


class PaymentsFacade(BaseFacade, IPaymentsFacade):
    def __init__(self, *, payment_dao: PaymentDao) -> None:
        super().__init__()
        self.payment_dao = payment_dao

    @observe("PaymentsFacade.get_settings")
    def get_settings(self, req: GetPaymentReq) -> PaymentResp:
        resp = self.payment_dao.get_or_create(req)
        req.db.commit()
        return resp

    @observe("PaymentsFacade.update_settings")
    def update_settings(self, req: UpdatePaymentReq) -> PaymentResp:
        resp = self.payment_dao.update(req)
        req.db.commit()
        return resp

    @observe("PaymentsFacade.get_billing")
    def get_billing(self, req: BillingReq) -> BillingResp:
        # Stripe stubbed: no receipts yet.
        return BillingResp(receipts=[], balance_due=0.0, currency="USD")
