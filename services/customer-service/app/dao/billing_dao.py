from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import BillingRunResp, CreateBillingRunReq, GetBillingRunReq
from ..models import BillingRun


class BillingDao(BaseDao):
    """Persistence for billing runs (the per-period idempotency record)."""

    @observe("BillingDao.get_run")
    def get_run(self, req: GetBillingRunReq) -> BillingRunResp:
        run = req.db.scalar(
            select(BillingRun).where(
                BillingRun.customer_id == req.customer_id, BillingRun.period == req.period
            )
        )
        return BillingRunResp(run=run)

    @observe("BillingDao.create_run")
    def create_run(self, req: CreateBillingRunReq) -> BillingRunResp:
        run = BillingRun(
            customer_id=req.customer_id, period=req.period, plan_name=req.plan_name,
            amount=req.amount, currency=req.currency, invoice_id=req.invoice_id,
            status=req.status, line_items=req.line_items or [],
        )
        req.db.add(run)
        req.db.flush()
        return BillingRunResp(run=run)
