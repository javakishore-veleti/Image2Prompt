from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import ProxyCustomersReq, ProxyCustomersResp
from ..services.customer_directory_service import CustomerDirectoryService
from .interfaces import ICustomersFacade


class CustomersFacade(BaseFacade, ICustomersFacade):
    def __init__(self, *, directory_service: CustomerDirectoryService) -> None:
        super().__init__()
        self.directory_service = directory_service

    @observe("CustomersFacade.search_customers")
    async def search_customers(self, req: ProxyCustomersReq) -> ProxyCustomersResp:
        return await self.directory_service.search(req)
