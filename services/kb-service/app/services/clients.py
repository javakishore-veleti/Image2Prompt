"""Cross-service HTTP clients (graceful — failures degrade, never raise)."""

from __future__ import annotations

import httpx

from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings


class SubscriptionClient(BaseService):
    """Reads a customer's plan from admin-service to gate KB tech stacks."""

    @observe("SubscriptionClient.get")
    async def get_customer_subscription(self, customer_id: str) -> dict:
        url = f"{settings.admin_service_url}/internal/subscriptions/customer/{customer_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url)
                r.raise_for_status()
                return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning("subscription lookup failed: %s", exc)
            return {"has_subscription": False, "stacks": [], "error": str(exc)}


class GenerationClient(BaseService):
    """Resolves selected Image2Prompt generations from image-processing-service."""

    @observe("GenerationClient.resolve")
    async def resolve(self, customer_id: str, request_ids: list[str]) -> list[dict]:
        url = f"{settings.image_service_url}/internal/requests/resolve"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, json={"customer_id": customer_id, "request_ids": request_ids})
                r.raise_for_status()
                return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning("generation resolve failed: %s", exc)
            return []
