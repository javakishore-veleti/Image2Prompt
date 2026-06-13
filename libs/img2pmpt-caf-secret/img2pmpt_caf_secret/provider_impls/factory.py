"""Resolves the active provider from config. Raises ProviderError if the selected
provider is unknown or its feature toggle is disabled."""

from __future__ import annotations

from ..config import CafSecretSettings
from .interfaces import ISecretProvider


class ProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def build_provider(settings: CafSecretSettings) -> ISecretProvider:
    provider = (settings.provider or "env").lower()

    if not settings.enabled_for(provider):
        raise ProviderError(
            "provider_disabled",
            f"Secret provider '{provider}' is selected but its feature toggle "
            f"(CAF_SECRET_{provider.upper()}_ENABLED) is false.",
        )

    if provider == "env":
        from .env_file_provider import EnvFileProvider

        return EnvFileProvider(settings)
    if provider == "aws":
        from .aws_secrets_provider import AwsSecretsManagerProvider

        return AwsSecretsManagerProvider(settings)
    if provider == "azure":
        from .azure_keyvault_provider import AzureKeyVaultProvider

        return AzureKeyVaultProvider(settings)
    if provider == "gcp":
        from .gcp_secret_manager_provider import GcpSecretManagerProvider

        return GcpSecretManagerProvider(settings)

    raise ProviderError("unknown_provider", f"Unknown secret provider: {provider!r}")
