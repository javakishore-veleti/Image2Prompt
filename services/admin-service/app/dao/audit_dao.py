from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select

from image2prompt_shared.base import utcnow
from image2prompt_shared.dtos import BaseResp
from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import AuditListResp, ListAuditReq, RecordAuditReq
from ..models import AuditLog


class AuditDao(BaseDao):
    @observe("AuditDao.record")
    def record(self, req: RecordAuditReq) -> BaseResp:
        # flush only — the caller commits within the same transaction as the action.
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
        # Also emit a structured line so the entry lands in the central log/OTel
        # pipeline (SIEM), independent of the DB row.
        self.log.info(
            "audit action=%s actor=%s target=%s", req.action, req.actor_email or "-", req.target or "-"
        )
        return BaseResp()

    @observe("AuditDao.list")
    def list(self, req: ListAuditReq) -> AuditListResp:
        conds = []
        if req.action:
            conds.append(AuditLog.action == req.action)
        if req.actor:
            conds.append(AuditLog.actor_email.ilike(f"%{req.actor}%"))
        if req.days:
            conds.append(AuditLog.created_at >= utcnow() - timedelta(days=req.days))
        total = int(req.db.scalar(select(func.count(AuditLog.id)).where(*conds)) or 0)
        stmt = (
            select(AuditLog)
            .where(*conds)
            .order_by(AuditLog.created_at.desc())
            .limit(req.limit)
            .offset(req.offset)
        )
        return AuditListResp(entries=list(req.db.scalars(stmt).all()), total=total)
