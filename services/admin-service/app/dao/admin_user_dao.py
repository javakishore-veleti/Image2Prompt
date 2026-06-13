from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe
from image2prompt_shared.security import hash_password

from ..dtos.internal_dtos import (
    AdminUserListResp,
    AdminUserResp,
    CreateAdminReq,
    DeleteAdminReq,
    GetAdminByEmailReq,
    ListAdminsReq,
)
from ..models import AdminUser


class AdminUserDao(BaseDao):
    @observe("AdminUserDao.get_by_email")
    def get_by_email(self, req: GetAdminByEmailReq) -> AdminUserResp:
        admin = req.db.scalar(select(AdminUser).where(AdminUser.email == req.email))
        return AdminUserResp(admin=admin)

    @observe("AdminUserDao.create")
    def create(self, req: CreateAdminReq) -> AdminUserResp:
        if req.db.scalar(select(AdminUser).where(AdminUser.email == req.email)):
            return AdminUserResp.failure(error_code="conflict", error_message="Email already exists")
        admin = AdminUser(
            email=req.email, password_hash=hash_password(req.password), role=req.role
        )
        req.db.add(admin)
        req.db.flush()
        return AdminUserResp(admin=admin)

    @observe("AdminUserDao.list")
    def list(self, req: ListAdminsReq) -> AdminUserListResp:
        rows = req.db.scalars(select(AdminUser).order_by(AdminUser.created_at.desc())).all()
        return AdminUserListResp(admins=list(rows))

    @observe("AdminUserDao.delete")
    def delete(self, req: DeleteAdminReq) -> AdminUserResp:
        admin = req.db.get(AdminUser, req.admin_id)
        if admin is None:
            return AdminUserResp.failure(error_code="not_found", error_message="Admin not found")
        req.db.delete(admin)
        req.db.flush()
        return AdminUserResp(admin=admin)
