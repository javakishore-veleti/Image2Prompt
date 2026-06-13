from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

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

    def count_recent(self, db: Session, *, actor_id: str, action: str, since: datetime) -> int:
        return int(
            db.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.actor_id == actor_id,
                    AuditLog.action == action,
                    AuditLog.created_at >= since,
                )
            )
            or 0
        )

    def last_event_at(self, db: Session, *, actor_id: str, action: str) -> datetime | None:
        return db.scalar(
            select(func.max(AuditLog.created_at)).where(
                AuditLog.actor_id == actor_id, AuditLog.action == action
            )
        )

    @observe("AuditDao.list_for_customer")
    def list_for_customer(self, req: ListActivityReq) -> ActivityListResp:
        # A customer sees activity attributed to their id, plus (for self-view)
        # failed-login attempts recorded against their email before a session
        # existed. When customer_email is None (admin cross-customer view), match
        # on actor_id only.
        if req.customer_email:
            cond = or_(AuditLog.actor_id == req.customer_id, AuditLog.actor_email == req.customer_email)
        else:
            cond = AuditLog.actor_id == req.customer_id
        total = int(req.db.scalar(select(func.count(AuditLog.id)).where(cond)) or 0)
        rows = list(
            req.db.scalars(
                select(AuditLog)
                .where(cond)
                .order_by(AuditLog.created_at.desc())
                .limit(req.limit)
                .offset(req.offset)
            ).all()
        )
        return ActivityListResp(entries=rows, total=total)
