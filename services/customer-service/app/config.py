from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class CustomerSettings(ServiceSettings):
    service_name: str = "customer-service"
    db_schema: str = "img2pmpt_customer"


settings = CustomerSettings()
