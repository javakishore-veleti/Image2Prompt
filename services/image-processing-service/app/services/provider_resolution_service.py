from __future__ import annotations

from image2prompt_shared.http_client import get_json
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings
from ..dtos.internal_dtos import ResolveProvidersReq, ResolveProvidersResp


class ProviderResolutionService(BaseService):
    """Resolves which providers to dispatch to, by combining admin-enabled
    providers, customer preferences, and any per-request override.

    Cascade (most specific wins): per-request override -> customer defaults ->
    all admin-enabled. Only globally-enabled providers survive.
    """

    @observe("ProviderResolutionService.resolve")
    async def resolve(self, req: ResolveProvidersReq) -> ResolveProvidersResp:
        prefs = await get_json(
            f"{settings.customer_service_url}/internal/customers/{req.customer_id}/preferences"
        )
        enabled = await get_json(
            f"{settings.admin_service_url}/internal/providers", params={"enabled": "true"}
        )
        enabled_map = {p["key"]: p["id"] for p in enabled}
        config_map = {p["key"]: p.get("config", {}) for p in enabled}

        default_keys = prefs.get("default_provider_keys", []) or []
        if req.requested_providers:
            candidate = req.requested_providers
        elif default_keys:
            candidate = default_keys
        else:
            candidate = list(enabled_map.keys())
        selected = [k for k in candidate if k in enabled_map]

        return ResolveProvidersResp(
            selected=selected,
            provider_id_map=enabled_map,
            config_map=config_map,
            storage_backend=prefs.get("storage_backend", "local"),
        )
