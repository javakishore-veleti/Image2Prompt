from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class CustomerSettings(ServiceSettings):
    service_name: str = "customer-service"
    db_schema: str = "img2pmpt_customer"
    # Stripe (billing). Empty key => billing reports "not configured", never errors.
    stripe_api_key: str = ""
    stripe_currency: str = "usd"

    # Google Drive OAuth (Connections). Empty client id => connect returns
    # "not configured"; the mock providers (onedrive/dropbox) still work.
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = (
        "http://localhost:8000/api/customer/me/connections/google/callback"
    )
    google_oauth_scopes: str = "openid email https://www.googleapis.com/auth/drive.readonly"
    google_oauth_success_redirect: str = "http://localhost:4200/connections"


settings = CustomerSettings()
