from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class AdminSettings(ServiceSettings):
    service_name: str = "admin-service"
    db_schema: str = "img2pmpt_admin"
    # Seeded on startup if no admin exists.
    admin_email: str = "admin@image2prompt.io"
    admin_password: str = "admin12345"
    # CSP violation rows last seen older than this are pruned on startup.
    csp_retention_days: int = 30


settings = AdminSettings()
