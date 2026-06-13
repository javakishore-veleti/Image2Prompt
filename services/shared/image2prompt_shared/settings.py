"""Common settings shared by every service.

Each service instantiates ``ServiceSettings`` (optionally with its own
``database_url`` default). Values are read from environment variables, so the
same image runs locally and under docker-compose with only env differences.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Auth / JWT (must match across services that issue/verify tokens) ---
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # --- Database (per service; overridden via env DATABASE_URL) ---
    database_url: str = "postgresql+psycopg://image2prompt:image2prompt@localhost:5432/postgres"

    # --- Internal service URLs (used for service-to-service calls) ---
    admin_service_url: str = "http://localhost:8001"
    customer_service_url: str = "http://localhost:8002"
    ai_adapters_url: str = "http://localhost:8003"
    image_service_url: str = "http://localhost:8004"
    gateway_url: str = "http://localhost:8000"

    # --- CORS (portals) ---
    cors_origins: str = "http://localhost:4200,http://localhost:4300"

    # --- Storage ---
    storage_backend: str = "local"
    local_storage_dir: str = "/data/uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
