"""The interface microservices depend on. They never import a provider directly."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .dtos import GetSecretReq, GetSecretResp, GetSecretsReq, GetSecretsResp


class ISecretClient(ABC):
    @abstractmethod
    def get_secret_by_key(self, req: GetSecretReq) -> GetSecretResp: ...

    @abstractmethod
    def get_secrets_by_keys(self, req: GetSecretsReq) -> GetSecretsResp: ...
