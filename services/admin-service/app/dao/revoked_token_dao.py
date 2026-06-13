from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..models import RevokedToken


@dataclass(kw_only=True)
class IsRevokedReq(BaseReq):
    db: Session
    jti: str


@dataclass(kw_only=True)
class IsRevokedResp(BaseResp):
    revoked: bool = False


@dataclass(kw_only=True)
class RevokeReq(BaseReq):
    db: Session
    jti: str
    expires_at: int = 0
    reason: str = "revoked"


class RevokedTokenDao(BaseDao):
    @observe("RevokedTokenDao.is_revoked")
    def is_revoked(self, req: IsRevokedReq) -> IsRevokedResp:
        hit = req.db.scalar(select(RevokedToken).where(RevokedToken.jti == req.jti))
        return IsRevokedResp(revoked=hit is not None)

    @observe("RevokedTokenDao.revoke")
    def revoke(self, req: RevokeReq) -> BaseResp:
        if not req.db.scalar(select(RevokedToken).where(RevokedToken.jti == req.jti)):
            req.db.add(RevokedToken(jti=req.jti, expires_at=req.expires_at, reason=req.reason))
            req.db.flush()
        return BaseResp()

    def prune_expired(self, db: Session, now_epoch: int) -> int:
        """Delete revoked-token rows whose token has already expired."""
        result = db.execute(
            delete(RevokedToken).where(
                RevokedToken.expires_at > 0, RevokedToken.expires_at < now_epoch
            )
        )
        db.commit()
        return result.rowcount or 0
