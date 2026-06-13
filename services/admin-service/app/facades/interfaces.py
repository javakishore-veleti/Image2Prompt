"""Facade interfaces for admin-service (controllers wire against these)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..dtos import internal_dtos as dto


class IAdminAuthFacade(ABC):
    @abstractmethod
    def login(self, req: "dto.AdminLoginReq") -> "dto.AdminAuthResp": ...

    @abstractmethod
    def refresh(self, req: "dto.AdminRefreshReq") -> "dto.AdminAuthResp": ...

    @abstractmethod
    def logout(self, req: "dto.AdminLogoutReq") -> "dto.AdminLogoutResp": ...


class IProvidersFacade(ABC):
    @abstractmethod
    def list_providers(self, req: "dto.ListProvidersReq") -> "dto.ProviderListResp": ...

    @abstractmethod
    def create_provider(self, req: "dto.CreateProviderReq") -> "dto.ProviderResp": ...

    @abstractmethod
    def update_provider(self, req: "dto.UpdateProviderReq") -> "dto.ProviderResp": ...


class IAnalyticsFacade(ABC):
    @abstractmethod
    async def get_analytics(self, req: "dto.GetAnalyticsReq") -> "dto.AnalyticsResp": ...


class ICustomersFacade(ABC):
    @abstractmethod
    async def search_customers(self, req: "dto.ProxyCustomersReq") -> "dto.ProxyCustomersResp": ...

    @abstractmethod
    async def get_connections(self, req: "dto.GetCustomerConnectionsReq") -> "dto.CustomerConnectionsResp": ...
