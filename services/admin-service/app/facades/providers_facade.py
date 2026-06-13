from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.provider_dao import ProviderDao
from ..dtos.internal_dtos import (
    CreateProviderReq,
    ListProvidersReq,
    ProviderListResp,
    ProviderResp,
    UpdateProviderReq,
)
from .interfaces import IProvidersFacade


class ProvidersFacade(BaseFacade, IProvidersFacade):
    def __init__(self, *, provider_dao: ProviderDao) -> None:
        super().__init__()
        self.provider_dao = provider_dao

    @observe("ProvidersFacade.list_providers")
    def list_providers(self, req: ListProvidersReq) -> ProviderListResp:
        return self.provider_dao.list(req)

    @observe("ProvidersFacade.create_provider")
    def create_provider(self, req: CreateProviderReq) -> ProviderResp:
        resp = self.provider_dao.create(req)
        if resp.success:
            req.db.commit()
        return resp

    @observe("ProvidersFacade.update_provider")
    def update_provider(self, req: UpdateProviderReq) -> ProviderResp:
        resp = self.provider_dao.update(req)
        if resp.success:
            req.db.commit()
        return resp
