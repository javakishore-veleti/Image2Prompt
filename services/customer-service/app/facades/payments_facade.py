from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..config import settings
from ..dao.customer_dao import CustomerDao
from ..dao.payment_dao import PaymentDao
from ..dtos.internal_dtos import (
    BillingReq,
    BillingResp,
    ChargeSubscriptionReq,
    ChargeSubscriptionResp,
    GetByIdReq,
    GetPaymentReq,
    PaymentResp,
    SetupIntentReq,
    SetupIntentResp,
    UpdatePaymentReq,
)
from ..services.billing_clients import BillingClient
from ..services.stripe_service import (
    CreateInvoiceReq,
    EnsureCustomerReq,
    InvoiceLineItem,
    ReceiptsReq,
    StripeService,
)
from ..services.stripe_service import SetupIntentReq as StripeSetupIntentReq
from .interfaces import IPaymentsFacade


class PaymentsFacade(BaseFacade, IPaymentsFacade):
    def __init__(
        self,
        *,
        payment_dao: PaymentDao,
        customer_dao: CustomerDao,
        stripe_service: StripeService,
        billing_client: BillingClient,
    ) -> None:
        super().__init__()
        self.payment_dao = payment_dao
        self.customer_dao = customer_dao
        self.stripe_service = stripe_service
        self.billing_client = billing_client

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

    def _compute_subscription(self, customer_id: str) -> dict:
        """The current KB subscription charge: for each tech stack the customer
        actually has KBs in, charge the plan's monthly_cost for that stack. The
        result is the billable breakdown used by both the billing view and the
        invoice action. Cross-service lookups degrade to an empty/zero result."""
        sub = self.billing_client.get_subscription(customer_id)
        usage = self.billing_client.get_kb_usage(customer_id)
        prices = {s.get("stack"): float(s.get("monthly_cost") or 0) for s in (sub.get("stacks") or [])}
        line_items = []
        for u in usage:
            stack = u.get("stack")
            if not u.get("kb_count"):
                continue
            line_items.append(
                {
                    "stack": stack,
                    "kb_count": int(u.get("kb_count") or 0),
                    "doc_count": int(u.get("doc_count") or 0),
                    "monthly_cost": prices.get(stack, 0.0),
                }
            )
        return {
            "has_subscription": bool(sub.get("has_subscription")),
            "plan_name": sub.get("plan_name"),
            "line_items": line_items,
            "monthly_total": round(sum(li["monthly_cost"] for li in line_items), 2),
            "currency": settings.stripe_currency,
        }

    @observe("PaymentsFacade.get_billing")
    def get_billing(self, req: BillingReq) -> BillingResp:
        _, cid, configured = self._ensure_stripe_customer(db=req.db, customer_id=req.customer_id)
        receipts = self.stripe_service.list_receipts(ReceiptsReq(customer_id=cid))
        return BillingResp(
            configured=configured,
            receipts=receipts.receipts,
            balance_due=receipts.balance_due,
            currency=receipts.currency,
            subscription=self._compute_subscription(req.customer_id),
        )

    @observe("PaymentsFacade.charge_subscription")
    def charge_subscription(self, req: ChargeSubscriptionReq) -> ChargeSubscriptionResp:
        """Generate a Stripe invoice for the current month's KB subscription charges."""
        sub = self._compute_subscription(req.customer_id)
        _, cid, configured = self._ensure_stripe_customer(db=req.db, customer_id=req.customer_id)
        if not configured:
            return ChargeSubscriptionResp(
                configured=False, line_items=sub["line_items"],
                amount=sub["monthly_total"], currency=sub["currency"], status="stripe_not_configured",
            )
        line_items = [
            InvoiceLineItem(
                description=f"Project KB — {li['stack']} ({li['kb_count']} KB, {li['doc_count']} docs)",
                amount=li["monthly_cost"],
            )
            for li in sub["line_items"]
        ]
        inv = self.stripe_service.create_invoice(
            CreateInvoiceReq(customer_id=cid, line_items=line_items, currency=sub["currency"])
        )
        return ChargeSubscriptionResp(
            success=inv.success,
            configured=inv.configured,
            invoice_id=inv.invoice_id,
            hosted_invoice_url=inv.hosted_invoice_url,
            amount=inv.amount or sub["monthly_total"],
            currency=sub["currency"],
            status=inv.status,
            line_items=sub["line_items"],
            error_code=inv.error_code,
            error_message=inv.error_message,
        )
