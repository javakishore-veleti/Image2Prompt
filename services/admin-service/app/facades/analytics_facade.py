from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.provider_dao import ProviderDao
from ..dtos.internal_dtos import (
    AnalyticsResp,
    FetchAnalyticsReq,
    GetAnalyticsReq,
    ListProvidersReq,
)
from ..services.analytics_service import AnalyticsService
from .interfaces import IAnalyticsFacade


class AnalyticsFacade(BaseFacade, IAnalyticsFacade):
    def __init__(self, *, provider_dao: ProviderDao, analytics_service: AnalyticsService) -> None:
        super().__init__()
        self.provider_dao = provider_dao
        self.analytics_service = analytics_service

    @observe("AnalyticsFacade.get_analytics")
    async def get_analytics(self, req: GetAnalyticsReq) -> AnalyticsResp:
        providers = self.provider_dao.list(ListProvidersReq(db=req.db)).providers
        remote = await self.analytics_service.fetch(FetchAnalyticsReq(days=req.days))
        return AnalyticsResp(
            customers=remote.customers,
            providers_total=len(providers),
            providers_enabled=sum(1 for p in providers if p.enabled),
            image_stats=remote.image_stats,
        )
