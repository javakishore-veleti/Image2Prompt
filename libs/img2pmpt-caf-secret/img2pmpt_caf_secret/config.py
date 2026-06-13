"""CAF secret settings — selects the provider and holds per-provider config.

All read from env with the ``CAF_SECRET_`` prefix, e.g. ``CAF_SECRET_PROVIDER``,
``CAF_SECRET_AWS_REGION``. A provider only works if BOTH selected and enabled.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CafSecretSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CAF_SECRET_", env_file=".env", extra="ignore")

    # Which provider to use: env | aws | azure | gcp
    provider: str = "env"

    # Per-provider feature toggles. The selected provider must also be enabled.
    env_enabled: bool = True
    aws_enabled: bool = False
    azure_enabled: bool = False
    gcp_enabled: bool = False

    # EnvFileProvider: optional extra .env-style file to overlay on os.environ.
    env_file_path: str = ""

    # AWS Secrets Manager: a single secret holding a JSON object of key->value.
    aws_region: str = "us-east-1"
    aws_secret_name: str = "img2pmpt/app"

    # Azure Key Vault: each key is a separate secret named after the key.
    azure_vault_url: str = ""

    # GCP Secret Manager: secret id = prefix + key, version "latest".
    gcp_project_id: str = ""
    gcp_secret_prefix: str = "img2pmpt-"

    def enabled_for(self, provider: str) -> bool:
        return {
            "env": self.env_enabled,
            "aws": self.aws_enabled,
            "azure": self.azure_enabled,
            "gcp": self.gcp_enabled,
        }.get(provider, False)
