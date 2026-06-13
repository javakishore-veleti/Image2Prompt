"""Internal req/resp dataclasses for admin-service (facade -> service -> dao)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from image2prompt_shared.dtos import BaseReq, BaseResp

from ..models import AdminUser, Provider


# --- auth ---
@dataclass(kw_only=True)
class AdminLoginReq(BaseReq):
    db: Session
    email: str
    password: str


@dataclass(kw_only=True)
class AdminRefreshReq(BaseReq):
    db: Session
    refresh_token: str


@dataclass(kw_only=True)
class AdminLogoutReq(BaseReq):
    db: Session
    refresh_token: str


@dataclass(kw_only=True)
class AdminLogoutResp(BaseResp):
    pass


@dataclass(kw_only=True)
class AdminAuthResp(BaseResp):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    email: Optional[str] = None
    role: str = "admin"


@dataclass(kw_only=True)
class GetAdminByEmailReq(BaseReq):
    db: Session
    email: str


@dataclass(kw_only=True)
class AdminUserResp(BaseResp):
    admin: Optional[AdminUser] = None


@dataclass(kw_only=True)
class CreateAdminReq(BaseReq):
    db: Session
    email: str
    password: str
    role: str = "viewer"


@dataclass(kw_only=True)
class ListAdminsReq(BaseReq):
    db: Session


@dataclass(kw_only=True)
class UpdateAdminReq(BaseReq):
    db: Session
    admin_id: str
    actor_id: str
    role: Optional[str] = None
    password: Optional[str] = None


@dataclass(kw_only=True)
class DeleteAdminReq(BaseReq):
    db: Session
    admin_id: str
    actor_id: str


@dataclass(kw_only=True)
class AdminUserListResp(BaseResp):
    admins: list[AdminUser] = field(default_factory=list)


# --- providers ---
@dataclass(kw_only=True)
class ListProvidersReq(BaseReq):
    db: Session
    enabled: Optional[bool] = None


@dataclass(kw_only=True)
class CreateProviderReq(BaseReq):
    db: Session
    key: str
    name: str
    category: str = "generic"
    enabled: bool = False
    config: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class GetProviderReq(BaseReq):
    db: Session
    provider_id: str


@dataclass(kw_only=True)
class UpdateProviderReq(BaseReq):
    db: Session
    provider_id: str
    name: Optional[str] = None
    category: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None


@dataclass(kw_only=True)
class ProviderResp(BaseResp):
    provider: Optional[Provider] = None


@dataclass(kw_only=True)
class ProviderListResp(BaseResp):
    providers: list[Provider] = field(default_factory=list)


# --- customers proxy (admin views customers held by customer-service) ---
@dataclass(kw_only=True)
class ProxyCustomersReq(BaseReq):
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(kw_only=True)
class ProxyCustomersResp(BaseResp):
    customers: list = field(default_factory=list)


@dataclass(kw_only=True)
class GetCustomerConnectionsReq(BaseReq):
    customer_id: str


@dataclass(kw_only=True)
class CustomerConnectionsResp(BaseResp):
    connections: list = field(default_factory=list)


# --- analytics ---
@dataclass(kw_only=True)
class FetchAnalyticsReq(BaseReq):
    days: int = 14


@dataclass(kw_only=True)
class FetchAnalyticsResp(BaseResp):
    customers: int = 0
    image_stats: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class GetAnalyticsReq(BaseReq):
    db: Session
    days: int = 14


@dataclass(kw_only=True)
class AnalyticsResp(BaseResp):
    customers: int = 0
    providers_total: int = 0
    providers_enabled: int = 0
    image_stats: dict = field(default_factory=dict)
