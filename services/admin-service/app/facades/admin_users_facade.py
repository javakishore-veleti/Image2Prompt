from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.admin_user_dao import AdminUserDao
from ..dao.audit_dao import AuditDao
from ..dtos.internal_dtos import (
    AdminUserListResp,
    AdminUserResp,
    CreateAdminReq,
    DeleteAdminReq,
    ListAdminsReq,
    RecordAuditReq,
    UnlockAdminReq,
    UnlockResp,
    UpdateAdminReq,
)
from .interfaces import IAdminUsersFacade

_VALID_ROLES = {"superadmin", "admin", "viewer"}


class AdminUsersFacade(BaseFacade, IAdminUsersFacade):
    def __init__(self, *, admin_user_dao: AdminUserDao, audit_dao: AuditDao) -> None:
        super().__init__()
        self.admin_user_dao = admin_user_dao
        self.audit_dao = audit_dao

    def _audit(self, req, action: str, target: str, detail: dict) -> None:
        self.audit_dao.record(
            RecordAuditReq(
                db=req.db, action=action, target=target, detail=detail,
                actor_id=getattr(req, "actor_id", None), actor_email=getattr(req, "actor_email", None),
            )
        )

    @observe("AdminUsersFacade.create_admin")
    def create_admin(self, req: CreateAdminReq) -> AdminUserResp:
        if req.role not in _VALID_ROLES:
            return AdminUserResp.failure(
                error_code="bad_request", error_message=f"role must be one of {sorted(_VALID_ROLES)}"
            )
        resp = self.admin_user_dao.create(req)
        if resp.success:
            self._audit(req, "admin_user.create", req.email, {"role": req.role})
            req.db.commit()
        return resp

    @observe("AdminUsersFacade.list_admins")
    def list_admins(self, req: ListAdminsReq) -> AdminUserListResp:
        return self.admin_user_dao.list(req)

    @observe("AdminUsersFacade.update_admin")
    def update_admin(self, req: UpdateAdminReq) -> AdminUserResp:
        if req.role is not None and req.role not in _VALID_ROLES:
            return AdminUserResp.failure(
                error_code="bad_request", error_message=f"role must be one of {sorted(_VALID_ROLES)}"
            )
        if req.role is not None and req.admin_id == req.actor_id:
            return AdminUserResp.failure(
                error_code="bad_request", error_message="You cannot change your own role"
            )
        resp = self.admin_user_dao.update(req)
        if resp.success:
            self._audit(
                req, "admin_user.update", req.admin_id,
                {"role": req.role, "password_changed": req.password is not None},
            )
            req.db.commit()
        return resp

    @observe("AdminUsersFacade.unlock_admin", metric="admin.user.unlock")
    def unlock_admin(self, req: UnlockAdminReq) -> UnlockResp:
        # Reset the lockout floor for the target admin, and log who did it.
        self.audit_dao.record(RecordAuditReq(db=req.db, action="admin.login.unlock", actor_id=req.admin_id))
        self.audit_dao.record(
            RecordAuditReq(
                db=req.db, action="admin_user.unlock", actor_id=req.actor_id,
                actor_email=req.actor_email, target=req.admin_id,
            )
        )
        req.db.commit()
        return UnlockResp(message="Admin account unlocked.")

    @observe("AdminUsersFacade.delete_admin")
    def delete_admin(self, req: DeleteAdminReq) -> AdminUserResp:
        if req.admin_id == req.actor_id:
            return AdminUserResp.failure(
                error_code="bad_request", error_message="You cannot delete your own account"
            )
        resp = self.admin_user_dao.delete(req)
        if resp.success:
            self._audit(req, "admin_user.delete", req.admin_id, {})
            req.db.commit()
        return resp
