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
class AdminAuthResp(BaseResp):
    access_token: Optional[str] = None
    email: Optional[str] = None
    role: str = "admin"


@dataclass(kw_only=True)
class GetAdminByEmailReq(BaseReq):
    db: Session
    email: str


@dataclass(kw_only=True)
class AdminUserResp(BaseResp):
    admin: Optional[AdminUser] = None


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
