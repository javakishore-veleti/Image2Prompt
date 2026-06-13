from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..controllers.base import ProviderController
from ..dtos.internal_dtos import (
    InvokeReq,
    InvokeResp,
    ListProvidersReq,
    ListProvidersResp,
    ProviderInfoItem,
)
from ..services.invoke_service import InvokeService
from .interfaces import IInvokeFacade


class InvokeFacade(BaseFacade, IInvokeFacade):
    def __init__(
        self, *, invoke_service: InvokeService, registry: dict[str, ProviderController]
    ) -> None:
        super().__init__()
        self.invoke_service = invoke_service
        self.registry = registry

    @observe("InvokeFacade.invoke", metric="aiadapters.facade.invoke")
    async def invoke(self, req: InvokeReq) -> InvokeResp:
        return await self.invoke_service.dispatch(req)

    @observe("InvokeFacade.list_providers")
    def list_providers(self, req: ListProvidersReq) -> ListProvidersResp:
        items = [
            ProviderInfoItem(key=k, implemented=c.implemented) for k, c in self.registry.items()
        ]
        return ListProvidersResp(providers=items)
