"""Common settings shared by every service.

Each service instantiates ``ServiceSettings`` (optionally subclassing it). Values
are read from environment variables, so the same image runs locally and in
containers with only env differences.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .config_sources import CafSecretsSettingsSource


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority (high -> low): init args, env vars, .env file, CAF secret store,
        # file secrets. So explicit env still overrides; cloud secrets fill the
        # rest when CAF_SECRET_PROVIDER is aws/azure/gcp (no-op otherwise).
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            CafSecretsSettingsSource(settings_cls),
            file_secret_settings,
        )

    # --- Identity ---
    service_name: str = "service"

    # --- Auth / JWT (must match across services that issue/verify tokens) ---
    jwt_secret: str = "dev-insecure-secret-change-me-please-32b"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # --- Database (shared server; one DB, one schema per service) ---
    database_url: str = (
        "postgresql+psycopg://image2prompt:image2prompt@localhost:5432/image2prompt"
    )
    db_schema: str = "public"
    run_migrations_on_startup: bool = True

    # --- Internal service URLs (service-to-service calls) ---
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
    # S3
    s3_bucket: str = ""
    s3_prefix: str = "uploads/"
    # Azure Blob
    azure_blob_container: str = ""
    azure_storage_connection_string: str = ""
    azure_storage_account_url: str = ""
    # GCP Cloud Storage
    gcs_bucket: str = ""
    gcs_prefix: str = "uploads/"

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = False

    # --- Observability (OpenTelemetry; the Python equivalent of Micrometer) ---
    # All disabled-by-default and fully fail-safe: if the collector is down or the
    # SDK is missing, the app still runs (calls become no-ops).
    otel_enabled: bool = False
    otel_service_namespace: str = "image2prompt"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_traces_enabled: bool = True
    otel_metrics_enabled: bool = True
    otel_span_attrs_enabled: bool = True
    otel_console_fallback: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")
