from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from image2prompt_shared.base import TimestampMixin, UUIDPkMixin

from .db import Base


class AdminUser(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="admin")


class Provider(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "providers"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), default="generic")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class RevokedToken(Base, UUIDPkMixin, TimestampMixin):
    """Denylist of revoked JWT ids (jti) — admin refresh tokens."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[int] = mapped_column(BigInteger, default=0)
    reason: Mapped[str] = mapped_column(String(50), default="revoked")


class AuditLog(Base, UUIDPkMixin, TimestampMixin):
    """Append-only record of sensitive admin actions (provider/credential changes,
    maintenance). ``detail`` never contains secret values — only key names."""

    __tablename__ = "audit_log"

    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class SubscriptionPlan(Base, UUIDPkMixin, TimestampMixin):
    """A named subscription plan that gates which KB tech stacks a customer may use
    and what each costs. ``stacks`` is a list of {stack, monthly_cost} — the stacks
    present are the ones the plan allows."""

    __tablename__ = "subscription_plans"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    stacks: Mapped[list] = mapped_column(JSON, default=list)
    # Per-plan quotas (NULL = unlimited). Enforced by kb-service at create/ingest.
    max_kbs: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    max_docs_per_kb: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class CustomerSubscription(Base, UUIDPkMixin, TimestampMixin):
    """Assigns a customer to a plan (one active plan per customer). customer_email is
    denormalized for admin reporting without a cross-service lookup."""

    __tablename__ = "customer_subscriptions"

    customer_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(50), default="active")


class CspViolation(Base, UUIDPkMixin, TimestampMixin):
    """A Content-Security-Policy violation report forwarded by the gateway.
    Normalized from both report-uri and Reporting-API payloads.

    Deduped by ``fingerprint``: identical violations bump ``count`` (and
    ``updated_at`` = last seen) instead of inserting a new row, so a noisy policy
    can't flood the table. Old rows are pruned on startup by retention age."""

    __tablename__ = "csp_violations"

    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    count: Mapped[int] = mapped_column(BigInteger, default=1, server_default="1")
    document_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    violated_directive: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    blocked_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
