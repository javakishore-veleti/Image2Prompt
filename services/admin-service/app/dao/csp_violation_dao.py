from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from image2prompt_shared.base import utcnow
from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    CspStatsReq,
    CspStatsResp,
    CspViolationListResp,
    CspViolationResp,
    IngestViolationReq,
    ListViolationsReq,
)
from ..models import CspViolation


def _fingerprint(req: IngestViolationReq) -> str:
    parts = [
        req.violated_directive or "",
        req.blocked_uri or "",
        req.document_uri or "",
        req.source_file or "",
        str(req.line_number or ""),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


class CspViolationDao(BaseDao):
    @observe("CspViolationDao.create")
    def create(self, req: IngestViolationReq) -> CspViolationResp:
        # Dedupe: identical violations bump count (and updated_at = last seen)
        # instead of inserting a new row.
        fp = _fingerprint(req)
        existing = req.db.scalar(select(CspViolation).where(CspViolation.fingerprint == fp))
        if existing is not None:
            existing.count = (existing.count or 1) + 1
            existing.updated_at = utcnow()
            req.db.flush()
            return CspViolationResp(violation=existing)
        row = CspViolation(
            fingerprint=fp,
            count=1,
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
                select(CspViolation).order_by(CspViolation.updated_at.desc()).limit(req.limit)
            ).all()
        )
        # Aggregate by directive using the per-row counts (reflects true volume).
        summary = [
            {"directive": d or "(unknown)", "count": int(c or 0)}
            for d, c in req.db.execute(
                select(CspViolation.violated_directive, func.sum(CspViolation.count))
                .group_by(CspViolation.violated_directive)
                .order_by(func.sum(CspViolation.count).desc())
            ).all()
        ]
        total = int(req.db.scalar(select(func.sum(CspViolation.count))) or 0)
        return CspViolationListResp(violations=rows, summary=summary, total=total)

    @observe("CspViolationDao.stats")
    def stats(self, req: CspStatsReq) -> CspStatsResp:
        total = int(req.db.scalar(select(func.sum(CspViolation.count))) or 0)
        distinct = int(req.db.scalar(select(func.count(CspViolation.id))) or 0)
        top = req.db.execute(
            select(CspViolation.violated_directive)
            .group_by(CspViolation.violated_directive)
            .order_by(func.sum(CspViolation.count).desc())
            .limit(1)
        ).scalar()
        return CspStatsResp(total=total, distinct=distinct, top_directive=top)

    def prune_older_than(self, db: Session, cutoff: datetime) -> int:
        """Delete violations last seen before ``cutoff``. Returns rows removed."""
        result = db.execute(delete(CspViolation).where(CspViolation.updated_at < cutoff))
        db.commit()
        return result.rowcount or 0
