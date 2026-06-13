"""Facade interfaces for admin-service (controllers wire against these)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..dtos import internal_dtos as dto


class IAdminAuthFacade(ABC):
    @abstractmethod
    def login(self, req: "dto.AdminLoginReq") -> "dto.AdminAuthResp": ...


class IProvidersFacade(ABC):
    @abstractmethod
    def list_providers(self, req: "dto.ListProvidersReq") -> "dto.ProviderListResp": ...

    @abstractmethod
    def create_provider(self, req: "dto.CreateProviderReq") -> "dto.ProviderResp": ...

    @abstractmethod
    def update_provider(self, req: "dto.UpdateProviderReq") -> "dto.ProviderResp": ...


class ICustomersFacade(ABC):
    @abstractmethod
    async def search_customers(self, req: "dto.ProxyCustomersReq") -> "dto.ProxyCustomersResp": ...
