"""Fetches cross-service analytics inputs (customer count + image-processing
stats). Failures degrade to zeros/empty rather than raising."""

from __future__ import annotations

import httpx

from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings
from ..dtos.internal_dtos import FetchAnalyticsReq, FetchAnalyticsResp


class AnalyticsService(BaseService):
    @observe("AnalyticsService.fetch")
    async def fetch(self, req: FetchAnalyticsReq) -> FetchAnalyticsResp:
        customers = 0
        image_stats: dict = {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                r = await client.get(f"{settings.customer_service_url}/internal/customers/count")
                r.raise_for_status()
                customers = r.json().get("count", 0)
            except httpx.HTTPError as exc:
                self.log.warning("customer count unavailable: %s", exc)
            try:
                r = await client.get(
                    f"{settings.image_service_url}/internal/stats", params={"days": req.days}
                )
                r.raise_for_status()
                image_stats = r.json()
            except httpx.HTTPError as exc:
                self.log.warning("image stats unavailable: %s", exc)
        return FetchAnalyticsResp(customers=customers, image_stats=image_stats)
