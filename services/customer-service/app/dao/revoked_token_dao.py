from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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
    family_id: Optional[str] = None


@dataclass(kw_only=True)
class IsFamilyRevokedReq(BaseReq):
    db: Session
    family_id: str


@dataclass(kw_only=True)
class RevokeFamilyReq(BaseReq):
    db: Session
    family_id: str
    expires_at: int = 0
    reason: str = "family_revoked"


# Sentinel jti prefix used for a family-level revocation marker (no real jti).
_FAMILY_MARKER = "family:"


class RevokedTokenDao(BaseDao):
    @observe("RevokedTokenDao.is_revoked")
    def is_revoked(self, req: IsRevokedReq) -> IsRevokedResp:
        hit = req.db.scalar(select(RevokedToken).where(RevokedToken.jti == req.jti))
        return IsRevokedResp(revoked=hit is not None)

    @observe("RevokedTokenDao.revoke")
    def revoke(self, req: RevokeReq) -> BaseResp:
        if not req.db.scalar(select(RevokedToken).where(RevokedToken.jti == req.jti)):
            req.db.add(
                RevokedToken(
                    jti=req.jti,
                    expires_at=req.expires_at,
                    reason=req.reason,
                    family_id=req.family_id,
                )
            )
            req.db.flush()
        return BaseResp()

    @observe("RevokedTokenDao.is_family_revoked")
    def is_family_revoked(self, req: IsFamilyRevokedReq) -> IsRevokedResp:
        """True if the whole family was revoked (e.g. after refresh-token reuse)."""
        marker = f"{_FAMILY_MARKER}{req.family_id}"
        hit = req.db.scalar(select(RevokedToken).where(RevokedToken.jti == marker))
        return IsRevokedResp(revoked=hit is not None)

    @observe("RevokedTokenDao.revoke_family")
    def revoke_family(self, req: RevokeFamilyReq) -> BaseResp:
        """Revoke an entire token family by inserting a family marker row. Any
        refresh token carrying this ``family_id`` is rejected from then on."""
        marker = f"{_FAMILY_MARKER}{req.family_id}"
        if not req.db.scalar(select(RevokedToken).where(RevokedToken.jti == marker)):
            req.db.add(
                RevokedToken(
                    jti=marker,
                    expires_at=req.expires_at,
                    reason=req.reason,
                    family_id=req.family_id,
                )
            )
            req.db.flush()
        return BaseResp()

    def prune_expired(self, db: Session, now_epoch: int) -> int:
        """Delete revoked-token rows whose underlying token has already expired
        (they can never be presented again). Returns rows removed."""
        result = db.execute(
            delete(RevokedToken).where(
                RevokedToken.expires_at > 0, RevokedToken.expires_at < now_epoch
            )
        )
        db.commit()
        return result.rowcount or 0
