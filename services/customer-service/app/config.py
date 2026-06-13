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

    # OneDrive / Microsoft Graph OAuth (Connections). Empty client id => connect
    # returns "not configured"; the mock onedrive/dropbox providers still work.
    microsoft_oauth_client_id: str = ""
    microsoft_oauth_client_secret: str = ""
    microsoft_oauth_tenant: str = "common"
    microsoft_oauth_redirect_uri: str = (
        "http://localhost:8000/api/customer/me/connections/onedrive/callback"
    )
    microsoft_oauth_scopes: str = "openid email offline_access Files.Read"
    microsoft_oauth_success_redirect: str = "http://localhost:4200/connections"

    # Customer portal base URL — used to build password-reset / email-verification
    # links that land back in the SPA.
    portal_base_url: str = "http://localhost:4200"
    password_reset_path: str = "/reset-password"
    email_verify_path: str = "/verify-email"
    password_reset_expire_minutes: int = 30
    email_verify_expire_minutes: int = 60 * 24


settings = CustomerSettings()
