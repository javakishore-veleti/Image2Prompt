from __future__ import annotations

from dataclasses import dataclass

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe
from image2prompt_shared.security import create_access_token, create_refresh_token

from ..config import settings


@dataclass(kw_only=True)
class IssueTokenReq(BaseReq):
    customer_id: str
    email: str


@dataclass(kw_only=True)
class IssueTokenResp(BaseResp):
    access_token: str = ""
    refresh_token: str = ""


class TokenService(BaseService):
    """Focused, reusable: issues customer access + refresh JWTs."""

    @observe("TokenService.issue")
    def issue(self, req: IssueTokenReq) -> IssueTokenResp:
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
        )
        return IssueTokenResp(access_token=access, refresh_token=refresh)
