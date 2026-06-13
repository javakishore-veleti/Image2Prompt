from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import admin_writer, current_admin, get_db, superadmin_only
from ..di import get_maintenance_facade
from ..dtos.internal_dtos import PruneReq, ReencryptReq, RotationStatusReq
from ..facades.interfaces import IMaintenanceFacade

router = APIRouter(prefix="/admin/maintenance", tags=["maintenance"])


@router.post("/prune")
def prune_now(
    _=Depends(admin_writer),
    db: Session = Depends(get_db),
    facade: IMaintenanceFacade = Depends(get_maintenance_facade),
):
    resp = ensure_ok(facade.prune_now(PruneReq(db=db)))
    return {"revoked_tokens": resp.revoked_tokens, "csp_violations": resp.csp_violations}


@router.post("/reencrypt")
async def reencrypt(
    _=Depends(superadmin_only),  # re-keying touches all stored secrets
    db: Session = Depends(get_db),
    facade: IMaintenanceFacade = Depends(get_maintenance_facade),
):
    resp = ensure_ok(await facade.reencrypt(ReencryptReq(db=db)))
    return {"providers": resp.providers, "connections": resp.connections}


@router.get("/rotation-status")
async def rotation_status(
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: IMaintenanceFacade = Depends(get_maintenance_facade),
):
    resp = ensure_ok(await facade.rotation_status(RotationStatusReq(db=db)))
    return {
        "key_id": resp.key_id,
        "providers": {"total": resp.provider_total, "stale": resp.provider_stale},
        "connections": {"total": resp.connection_total, "stale": resp.connection_stale},
    }
