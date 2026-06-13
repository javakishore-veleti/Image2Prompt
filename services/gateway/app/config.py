from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class GatewaySettings(ServiceSettings):
    service_name: str = "gateway"
    # Fixed-window rate limit per client (subject if authenticated, else IP).
    rate_limit_enabled: bool = True
    rate_limit_rpm: int = 120


settings = GatewaySettings()
