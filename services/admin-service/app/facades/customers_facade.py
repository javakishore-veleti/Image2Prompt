from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe


from ..dao.audit_dao import AuditDao
from ..dtos.internal_dtos import (
    CustomerActivityResp,
    CustomerConnectionsResp,
    GetCustomerActivityReq,
    GetCustomerConnectionsReq,
    ProxyCustomersReq,
    ProxyCustomersResp,
    RecordAuditReq,
    UnlockCustomerReq,
    UnlockResp,
)
from ..services.customer_directory_service import CustomerDirectoryService
from .interfaces import ICustomersFacade


class CustomersFacade(BaseFacade, ICustomersFacade):
    def __init__(self, *, directory_service: CustomerDirectoryService, audit_dao: AuditDao) -> None:
        super().__init__()
        self.directory_service = directory_service
        self.audit_dao = audit_dao

    @observe("CustomersFacade.search_customers")
    async def search_customers(self, req: ProxyCustomersReq) -> ProxyCustomersResp:
        return await self.directory_service.search(req)

    @observe("CustomersFacade.get_connections")
    async def get_connections(self, req: GetCustomerConnectionsReq) -> CustomerConnectionsResp:
        return await self.directory_service.get_connections(req)

    @observe("CustomersFacade.get_activity")
    async def get_activity(self, req: GetCustomerActivityReq) -> CustomerActivityResp:
        return await self.directory_service.get_activity(req)

    @observe("CustomersFacade.unlock_customer", metric="admin.customer.unlock")
    async def unlock_customer(self, req: UnlockCustomerReq) -> UnlockResp:
        res = await self.directory_service.unlock_customer(req.customer_id)
        if not res.success:
            return UnlockResp.failure(error_code=res.error_code or "upstream_error", error_message=res.error_message)
        # Record WHO unlocked WHOM in the admin's own (immutable) audit trail.
        self.audit_dao.record(
            RecordAuditReq(
                db=req.db, action="customer.account.unlock",
                actor_id=req.actor_id, actor_email=req.actor_email, target=req.customer_id,
            )
        )
        req.db.commit()
        return UnlockResp(message="Customer account unlocked.")
