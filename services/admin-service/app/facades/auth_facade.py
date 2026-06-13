from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe
from image2prompt_shared.security import verify_password

from ..dao.admin_user_dao import AdminUserDao
from ..dtos.internal_dtos import AdminAuthResp, AdminLoginReq, GetAdminByEmailReq
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
        token = self.token_service.issue(
            IssueAdminTokenReq(admin_id=admin.id, email=admin.email, role=admin.role)
        ).access_token
        Metrics.counter_add("admin.login.success")
        return AdminAuthResp(access_token=token, email=admin.email, role=admin.role)
