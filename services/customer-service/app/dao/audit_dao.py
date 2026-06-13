from __future__ import annotations

from sqlalchemy import or_, select

from image2prompt_shared.dtos import BaseResp
from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import ActivityListResp, ListActivityReq, RecordAuditReq
from ..models import AuditLog


class AuditDao(BaseDao):
    @observe("AuditDao.record")
    def record(self, req: RecordAuditReq) -> BaseResp:
        # flush only — the caller commits within the action's transaction.
        req.db.add(
            AuditLog(
                actor_id=req.actor_id,
                actor_email=req.actor_email,
                action=req.action,
                target=req.target,
                detail=req.detail or {},
            )
        )
        req.db.flush()
        self.log.info(
            "audit action=%s actor=%s target=%s", req.action, req.actor_email or "-", req.target or "-"
        )
        return BaseResp()

    @observe("AuditDao.list_for_customer")
    def list_for_customer(self, req: ListActivityReq) -> ActivityListResp:
        # A customer sees activity attributed to their id, plus failed-login
        # attempts recorded against their email before a session existed.
        rows = list(
            req.db.scalars(
                select(AuditLog)
                .where(or_(AuditLog.actor_id == req.customer_id, AuditLog.actor_email == req.customer_email))
                .order_by(AuditLog.created_at.desc())
                .limit(req.limit)
            ).all()
        )
        return ActivityListResp(entries=rows)
