from __future__ import annotations

from sqlalchemy import select

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
        return BaseResp()

    @observe("AuditDao.list")
    def list(self, req: ListAuditReq) -> AuditListResp:
        rows = list(
            req.db.scalars(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(req.limit)
            ).all()
        )
        return AuditListResp(entries=rows)
