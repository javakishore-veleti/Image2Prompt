from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import get_db, superadmin_only
from ..di import get_admin_users_facade
from ..dtos.internal_dtos import CreateAdminReq, DeleteAdminReq, ListAdminsReq, UpdateAdminReq
from ..facades.interfaces import IAdminUsersFacade
from ..schemas import AdminUserCreate, AdminUserOut, AdminUserUpdate

# Superadmin-only management of admin accounts + their roles.
router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[AdminUserOut])
def list_admins(
    _: Principal = Depends(superadmin_only),
    db: Session = Depends(get_db),
    facade: IAdminUsersFacade = Depends(get_admin_users_facade),
):
    return ensure_ok(facade.list_admins(ListAdminsReq(db=db))).admins


@router.post("", response_model=AdminUserOut, status_code=201)
def create_admin(
    payload: AdminUserCreate,
    principal: Principal = Depends(superadmin_only),
    db: Session = Depends(get_db),
    facade: IAdminUsersFacade = Depends(get_admin_users_facade),
):
    return ensure_ok(
        facade.create_admin(
            CreateAdminReq(
                db=db, email=payload.email, password=payload.password, role=payload.role,
                actor_id=principal.id, actor_email=principal.email,
            )
        )
    ).admin


@router.patch("/{admin_id}", response_model=AdminUserOut)
def update_admin(
    admin_id: str,
    payload: AdminUserUpdate,
    principal: Principal = Depends(superadmin_only),
    db: Session = Depends(get_db),
    facade: IAdminUsersFacade = Depends(get_admin_users_facade),
):
    return ensure_ok(
        facade.update_admin(
            UpdateAdminReq(
                db=db, admin_id=admin_id, actor_id=principal.id, actor_email=principal.email,
                role=payload.role, password=payload.password,
            )
        )
    ).admin


@router.delete("/{admin_id}", status_code=204)
def delete_admin(
    admin_id: str,
    principal: Principal = Depends(superadmin_only),
    db: Session = Depends(get_db),
    facade: IAdminUsersFacade = Depends(get_admin_users_facade),
):
    ensure_ok(
        facade.delete_admin(
            DeleteAdminReq(db=db, admin_id=admin_id, actor_id=principal.id, actor_email=principal.email)
        )
    )
