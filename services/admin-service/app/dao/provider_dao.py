from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    CreateProviderReq,
    ListProvidersReq,
    ProviderListResp,
    ProviderResp,
    UpdateProviderReq,
)
from ..models import Provider


class ProviderDao(BaseDao):
    @observe("ProviderDao.list")
    def list(self, req: ListProvidersReq) -> ProviderListResp:
        stmt = select(Provider)
        if req.enabled is not None:
            stmt = stmt.where(Provider.enabled == req.enabled)
        rows = req.db.scalars(stmt.order_by(Provider.name)).all()
        return ProviderListResp(providers=list(rows))

    @observe("ProviderDao.create")
    def create(self, req: CreateProviderReq) -> ProviderResp:
        exists = req.db.scalar(select(Provider).where(Provider.key == req.key))
        if exists is not None:
            return ProviderResp.failure(error_code="conflict", error_message="Provider key already exists")
        provider = Provider(
            key=req.key, name=req.name, category=req.category, enabled=req.enabled, config=req.config
        )
        req.db.add(provider)
        req.db.flush()
        return ProviderResp(provider=provider)

    @observe("ProviderDao.update")
    def update(self, req: UpdateProviderReq) -> ProviderResp:
        provider = req.db.get(Provider, req.provider_id)
        if provider is None:
            return ProviderResp.failure(error_code="not_found", error_message="Provider not found")
        if req.name is not None:
            provider.name = req.name
        if req.category is not None:
            provider.category = req.category
        if req.enabled is not None:
            provider.enabled = req.enabled
        if req.config is not None:
            provider.config = req.config
        req.db.flush()
        return ProviderResp(provider=provider)
