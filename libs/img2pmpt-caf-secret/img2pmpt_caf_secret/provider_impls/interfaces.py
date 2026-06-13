"""Provider interface + a base that derives bulk lookup from single lookup."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..client.dtos import GetSecretReq, GetSecretResp, GetSecretsReq, GetSecretsResp


class ISecretProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def get_secret_by_key(self, req: GetSecretReq) -> GetSecretResp: ...

    @abstractmethod
    def get_secrets_by_keys(self, req: GetSecretsReq) -> GetSecretsResp: ...


class BaseProvider(ISecretProvider):
    """Default ``get_secrets_by_keys`` looping over ``get_secret_by_key``.
    Providers with a cheaper bulk path (e.g. AWS JSON bundle) override it."""

    def get_secrets_by_keys(self, req: GetSecretsReq) -> GetSecretsResp:
        values: dict[str, str | None] = {}
        missing: list[str] = []
        for key in req.keys:
            r = self.get_secret_by_key(GetSecretReq(key=key))
            if not r.success:
                return GetSecretsResp(
                    success=False, error_code=r.error_code, error_message=r.error_message
                )
            values[key] = r.value
            if not r.found:
                missing.append(key)
        return GetSecretsResp(values=values, missing=missing)
