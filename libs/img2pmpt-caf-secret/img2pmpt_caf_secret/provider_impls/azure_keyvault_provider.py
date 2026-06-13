"""Azure Key Vault provider. Each key is a separate secret; Key Vault names allow
only alphanumerics and dashes, so underscores in keys map to dashes. SDK lazy."""

from __future__ import annotations

from ..client.dtos import GetSecretReq, GetSecretResp
from ..config import CafSecretSettings
from .interfaces import BaseProvider


def _to_kv_name(key: str) -> str:
    return key.replace("_", "-")


class AzureKeyVaultProvider(BaseProvider):
    name = "azure"

    def __init__(self, settings: CafSecretSettings) -> None:
        self._vault_url = settings.azure_vault_url
        self._client = None
        self._init_error: str | None = None

    def _kv_client(self):
        if self._client is not None or self._init_error is not None:
            return self._client
        try:
            from azure.identity import DefaultAzureCredential  # lazy
            from azure.keyvault.secrets import SecretClient as KvSecretClient

            self._client = KvSecretClient(
                vault_url=self._vault_url, credential=DefaultAzureCredential()
            )
        except Exception as exc:
            self._init_error = str(exc)
        return self._client

    def get_secret_by_key(self, req: GetSecretReq) -> GetSecretResp:
        client = self._kv_client()
        if client is None:
            return GetSecretResp(
                success=False, key=req.key, error_code="provider_error", error_message=self._init_error
            )
        try:
            secret = client.get_secret(_to_kv_name(req.key))
            return GetSecretResp(key=req.key, value=secret.value, found=True)
        except Exception as exc:
            # Not found vs. transport error — treat missing as found=False, default value.
            if "SecretNotFound" in exc.__class__.__name__ or "NotFound" in str(exc):
                return GetSecretResp(key=req.key, value=req.default, found=False)
            return GetSecretResp(
                success=False, key=req.key, error_code="provider_error", error_message=str(exc)
            )
