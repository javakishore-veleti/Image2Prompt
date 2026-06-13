from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.csp_violation_dao import CspViolationDao
from ..dao.provider_dao import ProviderDao
from ..dtos.internal_dtos import (
    AnalyticsResp,
    CspStatsReq,
    FetchAnalyticsReq,
    GetAnalyticsReq,
    ListProvidersReq,
)
from ..services.analytics_service import AnalyticsService
from .interfaces import IAnalyticsFacade


class AnalyticsFacade(BaseFacade, IAnalyticsFacade):
    def __init__(
        self,
        *,
        provider_dao: ProviderDao,
        analytics_service: AnalyticsService,
        csp_violation_dao: CspViolationDao,
    ) -> None:
        super().__init__()
        self.provider_dao = provider_dao
        self.analytics_service = analytics_service
        self.csp_violation_dao = csp_violation_dao

    @observe("AnalyticsFacade.get_analytics")
    async def get_analytics(self, req: GetAnalyticsReq) -> AnalyticsResp:
        providers = self.provider_dao.list(ListProvidersReq(db=req.db)).providers
        remote = await self.analytics_service.fetch(FetchAnalyticsReq(days=req.days))
        csp = self.csp_violation_dao.stats(CspStatsReq(db=req.db))
        return AnalyticsResp(
            customers=remote.customers,
            providers_total=len(providers),
            providers_enabled=sum(1 for p in providers if p.enabled),
            image_stats=remote.image_stats,
            csp_total=csp.total,
            csp_distinct=csp.distinct,
            csp_top_directive=csp.top_directive,
        )
