"""HTTP request/response models (pydantic) at the API boundary."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    email: str
    role: str = "admin"


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    key: str
    name: str
    category: str
    enabled: bool
    config: dict[str, Any] = {}


class ProviderCreate(BaseModel):
    key: str
    name: str
    category: str = "generic"
    enabled: bool = False
    config: dict[str, Any] = {}


class ProviderUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class CustomerOut(BaseModel):
    id: str
    email: str
    name: str | None = None
    status: str | None = None


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "viewer"


class AdminUserUpdate(BaseModel):
    role: str | None = None
    password: str | None = None


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    role: str


class CspViolationIn(BaseModel):
    """Normalized violation ingested from the gateway (already parsed)."""

    document_uri: str | None = None
    violated_directive: str | None = None
    blocked_uri: str | None = None
    source_file: str | None = None
    line_number: int | None = None
    disposition: str | None = None
    user_agent: str | None = None
    raw: dict[str, Any] = {}


class CspViolationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: Any
    updated_at: Any = None
    count: int = 1
    document_uri: str | None = None
    violated_directive: str | None = None
    blocked_uri: str | None = None
    source_file: str | None = None
    line_number: int | None = None
    disposition: str | None = None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: Any
    actor_email: str | None = None
    action: str
    target: str | None = None
    detail: dict[str, Any] = {}


class StackPrice(BaseModel):
    stack: str
    monthly_cost: float = 0.0


class PlanCreate(BaseModel):
    name: str
    description: str | None = None
    status: str = "active"
    stacks: list[StackPrice] = []


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    stacks: list[StackPrice] | None = None


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None = None
    status: str
    stacks: list[dict[str, Any]] = []


class AssignSubscription(BaseModel):
    customer_id: str
    customer_email: str | None = None


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    customer_email: str | None = None
    plan_id: str
    status: str


class CustomerSubscriptionView(BaseModel):
    """What kb-service consumes to gate KB tech stacks for a customer."""

    has_subscription: bool = False
    plan_id: str | None = None
    plan_name: str | None = None
    status: str | None = None
    stacks: list[dict[str, Any]] = []  # allowed stacks + cost


class CspSummaryItem(BaseModel):
    directive: str
    count: int


class CspDashboard(BaseModel):
    total: int
    summary: list[CspSummaryItem] = []
    violations: list[CspViolationOut] = []
