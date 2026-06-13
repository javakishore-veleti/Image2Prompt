from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.admin_user_dao import AdminUserDao
from ..dtos.internal_dtos import (
    AdminUserListResp,
    AdminUserResp,
    CreateAdminReq,
    DeleteAdminReq,
    ListAdminsReq,
)
from .interfaces import IAdminUsersFacade

_VALID_ROLES = {"superadmin", "admin", "viewer"}


class AdminUsersFacade(BaseFacade, IAdminUsersFacade):
    def __init__(self, *, admin_user_dao: AdminUserDao) -> None:
        super().__init__()
        self.admin_user_dao = admin_user_dao

    @observe("AdminUsersFacade.create_admin")
    def create_admin(self, req: CreateAdminReq) -> AdminUserResp:
        if req.role not in _VALID_ROLES:
            return AdminUserResp.failure(
                error_code="bad_request", error_message=f"role must be one of {sorted(_VALID_ROLES)}"
            )
        resp = self.admin_user_dao.create(req)
        if resp.success:
            req.db.commit()
        return resp

    @observe("AdminUsersFacade.list_admins")
    def list_admins(self, req: ListAdminsReq) -> AdminUserListResp:
        return self.admin_user_dao.list(req)

    @observe("AdminUsersFacade.delete_admin")
    def delete_admin(self, req: DeleteAdminReq) -> AdminUserResp:
        if req.admin_id == req.actor_id:
            return AdminUserResp.failure(
                error_code="bad_request", error_message="You cannot delete your own account"
            )
        resp = self.admin_user_dao.delete(req)
        if resp.success:
            req.db.commit()
        return resp
