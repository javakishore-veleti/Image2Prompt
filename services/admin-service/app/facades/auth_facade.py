from __future__ import annotations

import jwt

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe
from image2prompt_shared.security import decode_token, verify_password

from ..config import settings
from ..dao.admin_user_dao import AdminUserDao
from ..dtos.internal_dtos import AdminAuthResp, AdminLoginReq, AdminRefreshReq, GetAdminByEmailReq
from ..services.token_service import AdminTokenService, IssueAdminTokenReq
from .interfaces import IAdminAuthFacade


class AdminAuthFacade(BaseFacade, IAdminAuthFacade):
    def __init__(self, *, admin_user_dao: AdminUserDao, token_service: AdminTokenService) -> None:
        super().__init__()
        self.admin_user_dao = admin_user_dao
        self.token_service = token_service

    @observe("AdminAuthFacade.login", metric="admin.login")
    def login(self, req: AdminLoginReq) -> AdminAuthResp:
        result = self.admin_user_dao.get_by_email(GetAdminByEmailReq(db=req.db, email=req.email))
        admin = result.admin
        if admin is None or not verify_password(req.password, admin.password_hash):
            Metrics.counter_add("admin.login.failure")
            return AdminAuthResp.failure(error_code="unauthorized", error_message="Invalid credentials")
        tok = self.token_service.issue(
            IssueAdminTokenReq(admin_id=admin.id, email=admin.email, role=admin.role)
        )
        Metrics.counter_add("admin.login.success")
        return AdminAuthResp(
            access_token=tok.access_token, refresh_token=tok.refresh_token,
            email=admin.email, role=admin.role,
        )

    @observe("AdminAuthFacade.refresh", metric="admin.refresh")
    def refresh(self, req: AdminRefreshReq) -> AdminAuthResp:
        try:
            claims = decode_token(
                req.refresh_token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
            )
        except jwt.PyJWTError:
            return AdminAuthResp.failure(error_code="unauthorized", error_message="Invalid refresh token")
        if claims.get("typ") != "refresh":
            return AdminAuthResp.failure(error_code="unauthorized", error_message="Not a refresh token")
        tok = self.token_service.issue(
            IssueAdminTokenReq(
                admin_id=claims.get("sub", ""),
                email=claims.get("email", ""),
                role=claims.get("role", "admin"),
            )
        )
        return AdminAuthResp(
            access_token=tok.access_token, refresh_token=tok.refresh_token,
            email=claims.get("email", ""), role=claims.get("role", "admin"),
        )
