from __future__ import annotations

from sqlalchemy import func, select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    CspViolationListResp,
    CspViolationResp,
    IngestViolationReq,
    ListViolationsReq,
)
from ..models import CspViolation


class CspViolationDao(BaseDao):
    @observe("CspViolationDao.create")
    def create(self, req: IngestViolationReq) -> CspViolationResp:
        row = CspViolation(
            document_uri=req.document_uri,
            violated_directive=req.violated_directive,
            blocked_uri=req.blocked_uri,
            source_file=req.source_file,
            line_number=req.line_number,
            disposition=req.disposition,
            user_agent=req.user_agent,
            raw=req.raw,
        )
        req.db.add(row)
        req.db.flush()
        return CspViolationResp(violation=row)

    @observe("CspViolationDao.list")
    def list(self, req: ListViolationsReq) -> CspViolationListResp:
        rows = list(
            req.db.scalars(
                select(CspViolation).order_by(CspViolation.created_at.desc()).limit(req.limit)
            ).all()
        )
        # Aggregate counts by directive across the whole table (not just the page).
        summary = [
            {"directive": d or "(unknown)", "count": int(c)}
            for d, c in req.db.execute(
                select(CspViolation.violated_directive, func.count(CspViolation.id))
                .group_by(CspViolation.violated_directive)
                .order_by(func.count(CspViolation.id).desc())
            ).all()
        ]
        total = int(req.db.scalar(select(func.count(CspViolation.id))) or 0)
        return CspViolationListResp(violations=rows, summary=summary, total=total)
