from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe
from image2prompt_shared.security import create_access_token, create_refresh_token

from ..config import settings


@dataclass(kw_only=True)
class IssueTokenReq(BaseReq):
    customer_id: str
    email: str
    # Refresh-token family: a login starts a new family; a rotation keeps it.
    # When None, a fresh family id is minted.
    family_id: Optional[str] = None


@dataclass(kw_only=True)
class IssueTokenResp(BaseResp):
    access_token: str = ""
    refresh_token: str = ""
    family_id: str = ""


class TokenService(BaseService):
    """Focused, reusable: issues customer access + refresh JWTs.

    The refresh token carries a ``fid`` (family id) claim so that reuse of a
    rotated refresh token can revoke the entire family, not just that token.
    """

    @observe("TokenService.issue")
    def issue(self, req: IssueTokenReq) -> IssueTokenResp:
        family_id = req.family_id or str(uuid.uuid4())
        access = create_access_token(
            subject=req.customer_id,
            token_type="customer",
            email=req.email,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_expire_minutes,
        )
        refresh = create_refresh_token(
            subject=req.customer_id,
            email=req.email,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_refresh_expire_minutes,
            extra={"fid": family_id},
        )
        return IssueTokenResp(access_token=access, refresh_token=refresh, family_id=family_id)
