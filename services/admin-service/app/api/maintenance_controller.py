from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import admin_writer, get_db, superadmin_only
from ..di import get_maintenance_facade
from ..dtos.internal_dtos import PruneReq, ReencryptReq
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
