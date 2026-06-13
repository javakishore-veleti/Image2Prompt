from __future__ import annotations

import time
from datetime import timedelta

from image2prompt_shared.base import utcnow
from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..config import settings
from ..dao.audit_dao import AuditDao
from ..dao.csp_violation_dao import CspViolationDao
from ..dao.revoked_token_dao import RevokedTokenDao
from ..dtos.internal_dtos import (
    AuditListResp,
    ListAuditReq,
    PruneReq,
    PruneResp,
    RecordAuditReq,
    ReencryptReq,
    ReencryptResp,
    RotationStatusReq,
    RotationStatusResp,
)
from ..services.maintenance_service import MaintenanceService
from .interfaces import IMaintenanceFacade
from .providers_facade import ProvidersFacade


class MaintenanceFacade(BaseFacade, IMaintenanceFacade):
    def __init__(
        self,
        *,
        revoked_token_dao: RevokedTokenDao,
        csp_violation_dao: CspViolationDao,
        providers_facade: ProvidersFacade,
        maintenance_service: MaintenanceService,
        audit_dao: AuditDao,
    ) -> None:
        super().__init__()
        self.revoked_token_dao = revoked_token_dao
        self.csp_violation_dao = csp_violation_dao
        self.providers_facade = providers_facade
        self.maintenance_service = maintenance_service
        self.audit_dao = audit_dao

    @observe("MaintenanceFacade.prune_now", metric="admin.maintenance.prune")
    def prune_now(self, req: PruneReq) -> PruneResp:
        revoked = self.revoked_token_dao.prune_expired(req.db, int(time.time()))
        cutoff = utcnow() - timedelta(days=settings.csp_retention_days)
        csp = self.csp_violation_dao.prune_older_than(req.db, cutoff)
        self.audit_dao.record(
            RecordAuditReq(
                db=req.db, action="maintenance.prune", actor_id=req.actor_id,
                actor_email=req.actor_email, detail={"revoked_tokens": revoked, "csp_violations": csp},
            )
        )
        req.db.commit()
        return PruneResp(revoked_tokens=revoked, csp_violations=csp)

    @observe("MaintenanceFacade.reencrypt", metric="admin.maintenance.reencrypt")
    async def reencrypt(self, req: ReencryptReq) -> ReencryptResp:
        providers = self.providers_facade.reencrypt_configs(req.db)
        connections = await self.maintenance_service.reencrypt_customer_tokens()
        self.audit_dao.record(
            RecordAuditReq(
                db=req.db, action="maintenance.reencrypt", actor_id=req.actor_id,
                actor_email=req.actor_email, detail={"providers": providers, "connections": connections},
            )
        )
        req.db.commit()
        return ReencryptResp(providers=providers, connections=connections)

    @observe("MaintenanceFacade.list_audit")
    def list_audit(self, req: ListAuditReq) -> AuditListResp:
        return self.audit_dao.list(req)

    @observe("MaintenanceFacade.rotation_status")
    async def rotation_status(self, req: RotationStatusReq) -> RotationStatusResp:
        p_total, p_stale = self.providers_facade.rotation_status(req.db)
        c_total, c_stale = await self.maintenance_service.customer_rotation_status()
        return RotationStatusResp(
            key_id=self.providers_facade.cipher.current_key_id,
            provider_total=p_total,
            provider_stale=p_stale,
            connection_total=c_total,
            connection_stale=c_stale,
        )
