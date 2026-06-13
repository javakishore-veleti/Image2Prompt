from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import AdminUserResp, GetAdminByEmailReq
from ..models import AdminUser


class AdminUserDao(BaseDao):
    @observe("AdminUserDao.get_by_email")
    def get_by_email(self, req: GetAdminByEmailReq) -> AdminUserResp:
        admin = req.db.scalar(select(AdminUser).where(AdminUser.email == req.email))
        return AdminUserResp(admin=admin)
