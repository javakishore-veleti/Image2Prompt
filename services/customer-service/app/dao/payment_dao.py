from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import GetPaymentReq, PaymentResp, UpdatePaymentReq
from ..models import PaymentSettings


class PaymentDao(BaseDao):
    @observe("PaymentDao.get_or_create")
    def get_or_create(self, req: GetPaymentReq) -> PaymentResp:
        ps = req.db.scalar(
            select(PaymentSettings).where(PaymentSettings.customer_id == req.customer_id)
        )
        if ps is None:
            ps = PaymentSettings(customer_id=req.customer_id, data={})
            req.db.add(ps)
            req.db.flush()
        return PaymentResp(settings=ps)

    @observe("PaymentDao.update")
    def update(self, req: UpdatePaymentReq) -> PaymentResp:
        ps = req.db.scalar(
            select(PaymentSettings).where(PaymentSettings.customer_id == req.customer_id)
        )
        if ps is None:
            ps = PaymentSettings(customer_id=req.customer_id, data={})
            req.db.add(ps)
            req.db.flush()
        ps.data = req.data
        req.db.flush()
        return PaymentResp(settings=ps)
