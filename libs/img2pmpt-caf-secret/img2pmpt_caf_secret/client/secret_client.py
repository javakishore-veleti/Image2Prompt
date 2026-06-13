"""The client microservices use. Resolves the active provider lazily and
delegates; it's the only thing services import. Never raises on a provider
failure — returns a failed ``*Resp`` so callers stay robust."""

from __future__ import annotations

import threading

from ..config import CafSecretSettings
from ..provider_impls.factory import ProviderError, build_provider
from ..provider_impls.interfaces import ISecretProvider
from .dtos import GetSecretReq, GetSecretResp, GetSecretsReq, GetSecretsResp
from .interfaces import ISecretClient


class SecretClient(ISecretClient):
    def __init__(self, settings: CafSecretSettings | None = None) -> None:
        self._settings = settings or CafSecretSettings()
        self._provider: ISecretProvider | None = None
        self._provider_error: ProviderError | None = None

    @property
    def provider_name(self) -> str:
        return (self._settings.provider or "env").lower()

    def _provider_or_error(self) -> ISecretProvider | None:
        if self._provider is None and self._provider_error is None:
            try:
                self._provider = build_provider(self._settings)
            except ProviderError as exc:
                self._provider_error = exc
        return self._provider

    def get_secret_by_key(self, req: GetSecretReq) -> GetSecretResp:
        provider = self._provider_or_error()
        if provider is None:
            return GetSecretResp(
                success=False,
                key=req.key,
                value=req.default,
                error_code=self._provider_error.code,
                error_message=self._provider_error.message,
            )
        try:
            return provider.get_secret_by_key(req)
        except Exception as exc:  # provider must not break the caller
            return GetSecretResp(
                success=False, key=req.key, value=req.default,
                error_code="provider_error", error_message=str(exc),
            )

    def get_secrets_by_keys(self, req: GetSecretsReq) -> GetSecretsResp:
        provider = self._provider_or_error()
        if provider is None:
            return GetSecretsResp(
                success=False,
                error_code=self._provider_error.code,
                error_message=self._provider_error.message,
            )
        try:
            return provider.get_secrets_by_keys(req)
        except Exception as exc:
            return GetSecretsResp(
                success=False, error_code="provider_error", error_message=str(exc)
            )


_default_client: SecretClient | None = None
_lock = threading.Lock()


def get_secret_client() -> SecretClient:
    """Process-wide singleton client (shared-nothing: it holds only config + the
    resolved provider, no per-call state)."""
    global _default_client
    if _default_client is None:
        with _lock:
            if _default_client is None:
                _default_client = SecretClient()
    return _default_client
