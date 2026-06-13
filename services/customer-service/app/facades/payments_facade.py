from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.customer_dao import CustomerDao
from ..dao.payment_dao import PaymentDao
from ..dtos.internal_dtos import (
    BillingReq,
    BillingResp,
    GetByIdReq,
    GetPaymentReq,
    PaymentResp,
    SetupIntentReq,
    SetupIntentResp,
    UpdatePaymentReq,
)
from ..services.stripe_service import (
    EnsureCustomerReq,
    ReceiptsReq,
    StripeService,
)
from ..services.stripe_service import SetupIntentReq as StripeSetupIntentReq
from .interfaces import IPaymentsFacade


class PaymentsFacade(BaseFacade, IPaymentsFacade):
    def __init__(
        self, *, payment_dao: PaymentDao, customer_dao: CustomerDao, stripe_service: StripeService
    ) -> None:
        super().__init__()
        self.payment_dao = payment_dao
        self.customer_dao = customer_dao
        self.stripe_service = stripe_service

    def _ensure_stripe_customer(self, *, db, customer_id) -> tuple[object, str | None, bool]:
        """Return (payment_settings, stripe_customer_id, configured), creating the
        Stripe customer + persisting its id on first use."""
        ps = self.payment_dao.get_or_create(GetPaymentReq(db=db, customer_id=customer_id)).settings
        data = dict(ps.data or {})
        existing = data.get("stripe_customer_id")
        customer = self.customer_dao.get_by_id(GetByIdReq(db=db, customer_id=customer_id)).customer
        ensured = self.stripe_service.ensure_customer(
            EnsureCustomerReq(email=customer.email if customer else "", existing_customer_id=existing)
        )
        if ensured.configured and ensured.customer_id and ensured.customer_id != existing:
            data["stripe_customer_id"] = ensured.customer_id
            ps.data = data
            db.commit()
        return ps, data.get("stripe_customer_id"), ensured.configured

    @observe("PaymentsFacade.get_settings")
    def get_settings(self, req: GetPaymentReq) -> PaymentResp:
        ps, cid, configured = self._ensure_stripe_customer(db=req.db, customer_id=req.customer_id)
        return PaymentResp(settings=ps, configured=configured, stripe_customer_id=cid)

    @observe("PaymentsFacade.update_settings")
    def update_settings(self, req: UpdatePaymentReq) -> PaymentResp:
        resp = self.payment_dao.update(req)
        req.db.commit()
        return resp

    @observe("PaymentsFacade.create_setup_intent")
    def create_setup_intent(self, req: SetupIntentReq) -> SetupIntentResp:
        _, cid, configured = self._ensure_stripe_customer(db=req.db, customer_id=req.customer_id)
        if not configured:
            return SetupIntentResp(configured=False)
        si = self.stripe_service.create_setup_intent(StripeSetupIntentReq(customer_id=cid))
        return SetupIntentResp(
            success=si.success,
            configured=si.configured,
            client_secret=si.client_secret,
            error_code=si.error_code,
            error_message=si.error_message,
        )

    @observe("PaymentsFacade.get_billing")
    def get_billing(self, req: BillingReq) -> BillingResp:
        _, cid, configured = self._ensure_stripe_customer(db=req.db, customer_id=req.customer_id)
        receipts = self.stripe_service.list_receipts(ReceiptsReq(customer_id=cid))
        return BillingResp(
            configured=configured,
            receipts=receipts.receipts,
            balance_due=receipts.balance_due,
            currency=receipts.currency,
        )
