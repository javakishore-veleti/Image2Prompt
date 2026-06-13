"""Cross-service maintenance calls (re-encrypt customer tokens). Graceful:
failures degrade to a count of 0 rather than raising."""

from __future__ import annotations

import httpx

from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings


class MaintenanceService(BaseService):
    @observe("MaintenanceService.reencrypt_customer_tokens")
    async def reencrypt_customer_tokens(self) -> int:
        url = f"{settings.customer_service_url}/internal/maintenance/reencrypt-tokens"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url)
                r.raise_for_status()
                return int(r.json().get("reencrypted", 0))
        except (httpx.HTTPError, ValueError) as exc:
            self.log.warning("customer token re-encrypt unavailable: %s", exc)
            return 0
