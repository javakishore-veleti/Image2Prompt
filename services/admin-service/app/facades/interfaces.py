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


class IAdminUsersFacade(ABC):
    @abstractmethod
    def create_admin(self, req: "dto.CreateAdminReq") -> "dto.AdminUserResp": ...

    @abstractmethod
    def list_admins(self, req: "dto.ListAdminsReq") -> "dto.AdminUserListResp": ...

    @abstractmethod
    def update_admin(self, req: "dto.UpdateAdminReq") -> "dto.AdminUserResp": ...

    @abstractmethod
    def delete_admin(self, req: "dto.DeleteAdminReq") -> "dto.AdminUserResp": ...

    @abstractmethod
    def unlock_admin(self, req: "dto.UnlockAdminReq") -> "dto.UnlockResp": ...


class IProvidersFacade(ABC):
    @abstractmethod
    def list_providers(self, req: "dto.ListProvidersReq") -> "dto.ProviderListResp": ...

    @abstractmethod
    def create_provider(self, req: "dto.CreateProviderReq") -> "dto.ProviderResp": ...

    @abstractmethod
    def update_provider(self, req: "dto.UpdateProviderReq") -> "dto.ProviderResp": ...


class ICspFacade(ABC):
    @abstractmethod
    def ingest(self, req: "dto.IngestViolationReq") -> "dto.CspViolationResp": ...

    @abstractmethod
    def list_violations(self, req: "dto.ListViolationsReq") -> "dto.CspViolationListResp": ...


class ISubscriptionsFacade(ABC):
    @abstractmethod
    def create_plan(self, req: "dto.CreatePlanReq") -> "dto.PlanResp": ...

    @abstractmethod
    def update_plan(self, req: "dto.UpdatePlanReq") -> "dto.PlanResp": ...

    @abstractmethod
    def list_plans(self, req: "dto.ListPlansReq") -> "dto.PlanListResp": ...

    @abstractmethod
    def get_plan(self, req: "dto.GetPlanReq") -> "dto.PlanResp": ...

    @abstractmethod
    def assign(self, req: "dto.AssignSubscriptionReq") -> "dto.SubscriptionResp": ...

    @abstractmethod
    def list_plan_customers(self, req: "dto.ListPlanCustomersReq") -> "dto.SubscriptionListResp": ...

    @abstractmethod
    def get_customer_subscription(self, req: "dto.GetCustomerSubscriptionReq") -> "dto.SubscriptionResp": ...


class IMaintenanceFacade(ABC):
    @abstractmethod
    def prune_now(self, req: "dto.PruneReq") -> "dto.PruneResp": ...

    @abstractmethod
    async def reencrypt(self, req: "dto.ReencryptReq") -> "dto.ReencryptResp": ...

    @abstractmethod
    async def rotation_status(self, req: "dto.RotationStatusReq") -> "dto.RotationStatusResp": ...

    @abstractmethod
    def list_audit(self, req: "dto.ListAuditReq") -> "dto.AuditListResp": ...


class IAnalyticsFacade(ABC):
    @abstractmethod
    async def get_analytics(self, req: "dto.GetAnalyticsReq") -> "dto.AnalyticsResp": ...


class ICustomersFacade(ABC):
    @abstractmethod
    async def search_customers(self, req: "dto.ProxyCustomersReq") -> "dto.ProxyCustomersResp": ...

    @abstractmethod
    async def get_connections(self, req: "dto.GetCustomerConnectionsReq") -> "dto.CustomerConnectionsResp": ...

    @abstractmethod
    async def get_activity(self, req: "dto.GetCustomerActivityReq") -> "dto.CustomerActivityResp": ...

    @abstractmethod
    async def unlock_customer(self, req: "dto.UnlockCustomerReq") -> "dto.UnlockResp": ...
