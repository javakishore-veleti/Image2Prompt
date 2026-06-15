"""Stripe billing wrapper. The SDK is imported lazily and every method is safe:
with no STRIPE_API_KEY (or an API error) it returns ``configured=False`` /
empty rather than raising, so the app runs fine without Stripe set up."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings


@dataclass(kw_only=True)
class EnsureCustomerReq(BaseReq):
    email: str
    existing_customer_id: Optional[str] = None


@dataclass(kw_only=True)
class EnsureCustomerResp(BaseResp):
    configured: bool = False
    customer_id: Optional[str] = None


@dataclass(kw_only=True)
class SetupIntentReq(BaseReq):
    customer_id: Optional[str] = None


@dataclass(kw_only=True)
class SetupIntentResp(BaseResp):
    configured: bool = False
    client_secret: Optional[str] = None


@dataclass(kw_only=True)
class InvoiceLineItem:
    description: str
    amount: float  # in major currency units (e.g. dollars)


@dataclass(kw_only=True)
class CreateInvoiceReq(BaseReq):
    customer_id: Optional[str] = None
    line_items: list = field(default_factory=list)  # list[InvoiceLineItem]
    currency: str = "usd"


@dataclass(kw_only=True)
class CreateInvoiceResp(BaseResp):
    configured: bool = False
    invoice_id: Optional[str] = None
    hosted_invoice_url: Optional[str] = None
    amount: float = 0.0
    status: Optional[str] = None


@dataclass(kw_only=True)
class ReceiptsReq(BaseReq):
    customer_id: Optional[str] = None


@dataclass(kw_only=True)
class ReceiptsResp(BaseResp):
    configured: bool = False
    receipts: list = field(default_factory=list)
    balance_due: float = 0.0
    currency: str = "usd"


class StripeService(BaseService):
    def _ready(self) -> bool:
        return bool(settings.stripe_api_key)

    def _stripe(self):
        import stripe

        stripe.api_key = settings.stripe_api_key
        return stripe

    @observe("StripeService.ensure_customer")
    def ensure_customer(self, req: EnsureCustomerReq) -> EnsureCustomerResp:
        if not self._ready():
            return EnsureCustomerResp(configured=False)
        try:
            if req.existing_customer_id:
                return EnsureCustomerResp(configured=True, customer_id=req.existing_customer_id)
            customer = self._stripe().Customer.create(email=req.email)
            return EnsureCustomerResp(configured=True, customer_id=customer["id"])
        except Exception as exc:
            self.log.warning("stripe ensure_customer failed: %s", exc)
            return EnsureCustomerResp(success=False, error_code="upstream_error", error_message=str(exc))

    @observe("StripeService.create_setup_intent")
    def create_setup_intent(self, req: SetupIntentReq) -> SetupIntentResp:
        if not self._ready():
            return SetupIntentResp(configured=False)
        try:
            si = self._stripe().SetupIntent.create(customer=req.customer_id)
            return SetupIntentResp(configured=True, client_secret=si["client_secret"])
        except Exception as exc:
            return SetupIntentResp(success=False, error_code="upstream_error", error_message=str(exc))

    @observe("StripeService.create_invoice")
    def create_invoice(self, req: CreateInvoiceReq) -> CreateInvoiceResp:
        """Bill the customer for the given line items: create one Stripe invoice
        item per line, then a single invoice, and finalize it. No-op (configured=
        False) without a Stripe key or with no line items."""
        if not self._ready() or not req.customer_id:
            return CreateInvoiceResp(configured=self._ready())
        billable = [li for li in req.line_items if li.amount > 0]
        if not billable:
            return CreateInvoiceResp(configured=True, amount=0.0, status="nothing_to_bill")
        try:
            stripe = self._stripe()
            for li in billable:
                stripe.InvoiceItem.create(
                    customer=req.customer_id,
                    amount=int(round(li.amount * 100)),  # Stripe charges in minor units
                    currency=req.currency,
                    description=li.description,
                )
            invoice = stripe.Invoice.create(customer=req.customer_id, auto_advance=True)
            finalized = stripe.Invoice.finalize_invoice(invoice["id"])
            return CreateInvoiceResp(
                configured=True,
                invoice_id=finalized["id"],
                hosted_invoice_url=finalized.get("hosted_invoice_url"),
                amount=(finalized.get("amount_due", 0) or 0) / 100.0,
                status=finalized.get("status"),
            )
        except Exception as exc:
            self.log.warning("stripe create_invoice failed: %s", exc)
            return CreateInvoiceResp(success=False, error_code="upstream_error", error_message=str(exc))

    @observe("StripeService.list_receipts")
    def list_receipts(self, req: ReceiptsReq) -> ReceiptsResp:
        if not self._ready() or not req.customer_id:
            return ReceiptsResp(configured=self._ready(), currency=settings.stripe_currency)
        try:
            stripe = self._stripe()
            invoices = stripe.Invoice.list(customer=req.customer_id, limit=20)
            receipts = [
                {
                    "id": inv["id"],
                    "amount": (inv.get("amount_paid", 0) or 0) / 100.0,
                    "status": inv.get("status"),
                    "url": inv.get("hosted_invoice_url"),
                    "created": inv.get("created"),
                }
                for inv in invoices.get("data", [])
            ]
            balance = (stripe.Customer.retrieve(req.customer_id).get("balance", 0) or 0) / 100.0
            return ReceiptsResp(
                configured=True, receipts=receipts, balance_due=balance, currency=settings.stripe_currency
            )
        except Exception as exc:
            return ReceiptsResp(success=False, error_code="upstream_error", error_message=str(exc))
