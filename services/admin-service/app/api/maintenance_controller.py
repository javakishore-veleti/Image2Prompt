from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import admin_writer, current_admin, get_db, superadmin_only
from ..di import get_maintenance_facade
from ..dtos.internal_dtos import ListAuditReq, PruneReq, ReencryptReq, RotationStatusReq
from ..facades.interfaces import IMaintenanceFacade
from ..schemas import AuditOut

router = APIRouter(prefix="/admin/maintenance", tags=["maintenance"])
audit = APIRouter(prefix="/admin/audit-log", tags=["audit"])


@router.post("/prune")
def prune_now(
    principal: Principal = Depends(admin_writer),
    db: Session = Depends(get_db),
    facade: IMaintenanceFacade = Depends(get_maintenance_facade),
):
    resp = ensure_ok(
        facade.prune_now(PruneReq(db=db, actor_id=principal.id, actor_email=principal.email))
    )
    return {"revoked_tokens": resp.revoked_tokens, "csp_violations": resp.csp_violations}


@router.post("/reencrypt")
async def reencrypt(
    principal: Principal = Depends(superadmin_only),  # re-keying touches all stored secrets
    db: Session = Depends(get_db),
    facade: IMaintenanceFacade = Depends(get_maintenance_facade),
):
    resp = ensure_ok(
        await facade.reencrypt(ReencryptReq(db=db, actor_id=principal.id, actor_email=principal.email))
    )
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


@audit.get("", response_model=list[AuditOut])
def list_audit(
    limit: int = Query(default=100, le=500),
    action: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    days: int | None = Query(default=None, ge=1, le=3650),
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: IMaintenanceFacade = Depends(get_maintenance_facade),
):
    resp = ensure_ok(
        facade.list_audit(ListAuditReq(db=db, limit=limit, action=action, actor=actor, days=days))
    )
    return [AuditOut.model_validate(e) for e in resp.entries]


@audit.get("/export")
def export_audit(
    action: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    days: int | None = Query(default=None, ge=1, le=3650),
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: IMaintenanceFacade = Depends(get_maintenance_facade),
):
    """Download the (filtered) audit trail as newline-delimited JSON for archival/SIEM."""
    resp = ensure_ok(
        facade.list_audit(ListAuditReq(db=db, limit=10000, action=action, actor=actor, days=days))
    )
    body = "\n".join(AuditOut.model_validate(e).model_dump_json() for e in resp.entries)
    return Response(
        content=body,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="audit-log.ndjson"'},
    )
