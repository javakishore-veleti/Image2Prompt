from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class CustomerSettings(ServiceSettings):
    service_name: str = "customer-service"
    db_schema: str = "img2pmpt_customer"
    # Stripe (billing). Empty key => billing reports "not configured", never errors.
    stripe_api_key: str = ""
    stripe_currency: str = "usd"


settings = CustomerSettings()
