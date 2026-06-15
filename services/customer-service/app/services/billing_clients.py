"""Cross-service HTTP clients for billing (graceful — failures degrade, never
raise). admin-service supplies the customer's plan + per-stack pricing; kb-service
supplies how many KBs/docs the customer actually provisioned per tech stack.

Synchronous httpx because the payments facade/controller are sync (FastAPI runs
sync routes in a threadpool, so the blocking call doesn't stall the event loop)."""

from __future__ import annotations

import httpx

from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings


class BillingClient(BaseService):
    @observe("BillingClient.get_subscription")
    def get_subscription(self, customer_id: str) -> dict:
        """{has_subscription, plan_id, plan_name, status, stacks:[{stack,monthly_cost}]}."""
        url = f"{settings.admin_service_url}/internal/subscriptions/customer/{customer_id}"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
                r.raise_for_status()
                return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning("subscription lookup failed: %s", exc)
            return {"has_subscription": False, "stacks": []}

    @observe("BillingClient.get_kb_usage")
    def get_kb_usage(self, customer_id: str) -> list[dict]:
        """[{stack, kb_count, doc_count}] — the customer's provisioned KBs per stack."""
        url = f"{settings.kb_service_url}/internal/usage/customer/{customer_id}"
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(url)
                r.raise_for_status()
                return r.json().get("stacks", [])
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning("kb usage lookup failed: %s", exc)
            return []
