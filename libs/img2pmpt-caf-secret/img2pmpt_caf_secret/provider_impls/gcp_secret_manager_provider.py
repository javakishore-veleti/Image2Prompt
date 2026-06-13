"""GCP Secret Manager provider. Secret id = prefix + key (underscores -> dashes),
version 'latest'. SDK imported lazily."""

from __future__ import annotations

from ..client.dtos import GetSecretReq, GetSecretResp
from ..config import CafSecretSettings
from .interfaces import BaseProvider


class GcpSecretManagerProvider(BaseProvider):
    name = "gcp"

    def __init__(self, settings: CafSecretSettings) -> None:
        self._project_id = settings.gcp_project_id
        self._prefix = settings.gcp_secret_prefix
        self._client = None
        self._init_error: str | None = None

    def _secret_id(self, key: str) -> str:
        return f"{self._prefix}{key.replace('_', '-')}"

    def _sm_client(self):
        if self._client is not None or self._init_error is not None:
            return self._client
        try:
            from google.cloud import secretmanager  # lazy

            self._client = secretmanager.SecretManagerServiceClient()
        except Exception as exc:
            self._init_error = str(exc)
        return self._client

    def get_secret_by_key(self, req: GetSecretReq) -> GetSecretResp:
        client = self._sm_client()
        if client is None:
            return GetSecretResp(
                success=False, key=req.key, error_code="provider_error", error_message=self._init_error
            )
        try:
            name = f"projects/{self._project_id}/secrets/{self._secret_id(req.key)}/versions/latest"
            response = client.access_secret_version(name=name)
            value = response.payload.data.decode("utf-8")
            return GetSecretResp(key=req.key, value=value, found=True)
        except Exception as exc:
            if "NotFound" in exc.__class__.__name__ or "not found" in str(exc).lower():
                return GetSecretResp(key=req.key, value=req.default, found=False)
            return GetSecretResp(
                success=False, key=req.key, error_code="provider_error", error_message=str(exc)
            )
