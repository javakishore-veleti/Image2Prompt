from __future__ import annotations

from abc import ABC, abstractmethod

from ..dtos import internal_dtos as dto


class IInvokeFacade(ABC):
    @abstractmethod
    async def invoke(self, req: "dto.InvokeReq") -> "dto.InvokeResp": ...

    @abstractmethod
    def list_providers(self, req: "dto.ListProvidersReq") -> "dto.ListProvidersResp": ...
