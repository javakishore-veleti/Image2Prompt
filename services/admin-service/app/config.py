from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class AdminSettings(ServiceSettings):
    # Seeded on startup if no admin exists.
    admin_email: str = "admin@image2prompt.io"
    admin_password: str = "admin12345"


settings = AdminSettings()
