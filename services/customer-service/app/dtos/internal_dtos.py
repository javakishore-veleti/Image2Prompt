"""Internal req/resp dataclasses passed between facade -> service -> dao.

Every layer method takes exactly one ``*Req`` and returns one ``*Resp``. The DB
Session travels inside the Req (shared-nothing: singletons hold no session).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from image2prompt_shared.dtos import BaseReq, BaseResp

from ..models import Customer, CustomerPreference, PaymentSettings, Project


# --- auth ---
@dataclass(kw_only=True)
class SignupReq(BaseReq):
    db: Session
    email: str
    password: str
    name: Optional[str] = None


@dataclass(kw_only=True)
class LoginReq(BaseReq):
    db: Session
    email: str
    password: str


@dataclass(kw_only=True)
class AuthResp(BaseResp):
    access_token: Optional[str] = None
    customer_id: Optional[str] = None
    email: Optional[str] = None


# --- customer crud ---
@dataclass(kw_only=True)
class GetByEmailReq(BaseReq):
    db: Session
    email: str


@dataclass(kw_only=True)
class GetByIdReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class CreateCustomerReq(BaseReq):
    db: Session
    email: str
    password_hash: str
    name: Optional[str] = None


@dataclass(kw_only=True)
class CustomerResp(BaseResp):
    customer: Optional[Customer] = None


@dataclass(kw_only=True)
class SearchCustomersReq(BaseReq):
    db: Session
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(kw_only=True)
class CustomerListResp(BaseResp):
    customers: list[Customer] = field(default_factory=list)


# --- preferences ---
@dataclass(kw_only=True)
class GetPrefsReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class UpdatePrefsReq(BaseReq):
    db: Session
    customer_id: str
    default_provider_keys: Optional[list[str]] = None
    storage_backend: Optional[str] = None
    prefs: Optional[dict] = None


@dataclass(kw_only=True)
class PrefsResp(BaseResp):
    preference: Optional[CustomerPreference] = None


# --- projects ---
@dataclass(kw_only=True)
class ListProjectsReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class CreateProjectReq(BaseReq):
    db: Session
    customer_id: str
    name: str
    meta: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class GetProjectReq(BaseReq):
    db: Session
    customer_id: str
    project_id: str


@dataclass(kw_only=True)
class ProjectResp(BaseResp):
    project: Optional[Project] = None


@dataclass(kw_only=True)
class ProjectListResp(BaseResp):
    projects: list[Project] = field(default_factory=list)


# --- payments ---
@dataclass(kw_only=True)
class GetPaymentReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class UpdatePaymentReq(BaseReq):
    db: Session
    customer_id: str
    data: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class PaymentResp(BaseResp):
    settings: Optional[PaymentSettings] = None


@dataclass(kw_only=True)
class BillingReq(BaseReq):
    customer_id: str


@dataclass(kw_only=True)
class BillingResp(BaseResp):
    receipts: list = field(default_factory=list)
    balance_due: float = 0.0
    currency: str = "USD"
