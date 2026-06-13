from __future__ import annotations

from dataclasses import dataclass

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe
from image2prompt_shared.security import create_access_token

from ..config import settings


@dataclass(kw_only=True)
class IssueAdminTokenReq(BaseReq):
    admin_id: str
    email: str
    role: str = "admin"


@dataclass(kw_only=True)
class IssueAdminTokenResp(BaseResp):
    access_token: str = ""


class AdminTokenService(BaseService):
    @observe("AdminTokenService.issue")
    def issue(self, req: IssueAdminTokenReq) -> IssueAdminTokenResp:
        token = create_access_token(
            subject=req.admin_id,
            token_type="admin",
            email=req.email,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.jwt_expire_minutes,
            extra={"role": req.role},
        )
        return IssueAdminTokenResp(access_token=token)
