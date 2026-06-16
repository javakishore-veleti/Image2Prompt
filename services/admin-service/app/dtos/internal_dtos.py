"""Internal req/resp dataclasses for admin-service (facade -> service -> dao)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from image2prompt_shared.dtos import BaseReq, BaseResp

from ..models import (
    AdminUser,
    AuditLog,
    CspViolation,
    CustomerSubscription,
    Provider,
    SubscriptionPlan,
)


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
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass(kw_only=True)
class ListAdminsReq(BaseReq):
    db: Session


@dataclass(kw_only=True)
class UpdateAdminReq(BaseReq):
    db: Session
    admin_id: str
    actor_id: str
    actor_email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None


@dataclass(kw_only=True)
class DeleteAdminReq(BaseReq):
    db: Session
    admin_id: str
    actor_id: str
    actor_email: Optional[str] = None


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
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


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
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


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


@dataclass(kw_only=True)
class GetCustomerActivityReq(BaseReq):
    customer_id: str
    limit: int = 50
    offset: int = 0


@dataclass(kw_only=True)
class CustomerActivityResp(BaseResp):
    entries: list = field(default_factory=list)


@dataclass(kw_only=True)
class UnlockCustomerReq(BaseReq):
    db: Session
    customer_id: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass(kw_only=True)
class UnlockAdminReq(BaseReq):
    db: Session
    admin_id: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass(kw_only=True)
class UnlockResp(BaseResp):
    message: str = ""


# --- csp violations ---
@dataclass(kw_only=True)
class IngestViolationReq(BaseReq):
    db: Session
    document_uri: Optional[str] = None
    violated_directive: Optional[str] = None
    blocked_uri: Optional[str] = None
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    disposition: Optional[str] = None
    user_agent: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class ListViolationsReq(BaseReq):
    db: Session
    limit: int = 100


@dataclass(kw_only=True)
class CspViolationResp(BaseResp):
    violation: Optional[CspViolation] = None


@dataclass(kw_only=True)
class CspViolationListResp(BaseResp):
    violations: list[CspViolation] = field(default_factory=list)
    summary: list[dict] = field(default_factory=list)  # [{directive, count}]
    total: int = 0


@dataclass(kw_only=True)
class CspStatsReq(BaseReq):
    db: Session


@dataclass(kw_only=True)
class CspStatsResp(BaseResp):
    total: int = 0  # total reports (sum of per-row counts)
    distinct: int = 0  # distinct violations (rows)
    top_directive: Optional[str] = None


# --- audit log ---
@dataclass(kw_only=True)
class RecordAuditReq(BaseReq):
    db: Session
    action: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None
    target: Optional[str] = None
    detail: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class ListAuditReq(BaseReq):
    db: Session
    limit: int = 100
    offset: int = 0
    action: Optional[str] = None  # exact match
    actor: Optional[str] = None  # substring match on actor_email
    days: Optional[int] = None  # only entries from the last N days


@dataclass(kw_only=True)
class AuditListResp(BaseResp):
    entries: list[AuditLog] = field(default_factory=list)
    total: int = 0


# --- subscriptions ---
@dataclass(kw_only=True)
class CreatePlanReq(BaseReq):
    db: Session
    name: str
    description: Optional[str] = None
    status: str = "active"
    stacks: list = field(default_factory=list)  # [{stack, monthly_cost}]
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass(kw_only=True)
class UpdatePlanReq(BaseReq):
    db: Session
    plan_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    stacks: Optional[list] = None
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass(kw_only=True)
class ListPlansReq(BaseReq):
    db: Session
    search: Optional[str] = None


@dataclass(kw_only=True)
class GetPlanReq(BaseReq):
    db: Session
    plan_id: str


@dataclass(kw_only=True)
class PlanResp(BaseResp):
    plan: Optional[SubscriptionPlan] = None


@dataclass(kw_only=True)
class PlanListResp(BaseResp):
    plans: list[SubscriptionPlan] = field(default_factory=list)


@dataclass(kw_only=True)
class AssignSubscriptionReq(BaseReq):
    db: Session
    plan_id: str
    customer_id: str
    customer_email: Optional[str] = None
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass(kw_only=True)
class ListPlanCustomersReq(BaseReq):
    db: Session
    plan_id: str
    search: Optional[str] = None


@dataclass(kw_only=True)
class GetCustomerSubscriptionReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class SubscriptionResp(BaseResp):
    subscription: Optional[CustomerSubscription] = None
    plan: Optional[SubscriptionPlan] = None


@dataclass(kw_only=True)
class SubscriptionListResp(BaseResp):
    subscriptions: list[CustomerSubscription] = field(default_factory=list)


@dataclass(kw_only=True)
class ListActiveSubscriptionsReq(BaseReq):
    db: Session


@dataclass(kw_only=True)
class ActiveSubscriptionListResp(BaseResp):
    # one dict per active subscription, denormalized with the plan:
    # {customer_id, customer_email, plan_id, plan_name, status, stacks}
    items: list[dict] = field(default_factory=list)


# --- maintenance ---
@dataclass(kw_only=True)
class PruneReq(BaseReq):
    db: Session
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass(kw_only=True)
class PruneResp(BaseResp):
    revoked_tokens: int = 0
    csp_violations: int = 0


@dataclass(kw_only=True)
class ReencryptReq(BaseReq):
    db: Session
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None


@dataclass(kw_only=True)
class ReencryptResp(BaseResp):
    providers: int = 0
    connections: int = 0


@dataclass(kw_only=True)
class RotationStatusReq(BaseReq):
    db: Session


@dataclass(kw_only=True)
class RotationStatusResp(BaseResp):
    key_id: Optional[str] = None
    provider_total: int = 0
    provider_stale: int = 0
    connection_total: int = 0
    connection_stale: int = 0


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
    csp_total: int = 0
    csp_distinct: int = 0
    csp_top_directive: Optional[str] = None
