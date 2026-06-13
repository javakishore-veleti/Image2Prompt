from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class GatewaySettings(ServiceSettings):
    service_name: str = "gateway"


settings = GatewaySettings()
