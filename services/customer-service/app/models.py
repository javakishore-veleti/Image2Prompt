from __future__ import annotations

from sqlalchemy import JSON, BigInteger, Boolean, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from image2prompt_shared.base import TimestampMixin, UUIDPkMixin

from .db import Base


class Customer(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "customers"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")


class CustomerPreference(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "customer_preferences"

    customer_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    default_provider_keys: Mapped[list] = mapped_column(JSON, default=list)
    storage_backend: Mapped[str] = mapped_column(String(50), default="local")
    prefs: Mapped[dict] = mapped_column(JSON, default=dict)


class Project(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "projects"

    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(255))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class PaymentSettings(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "payment_settings"

    customer_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Connection(Base, UUIDPkMixin, TimestampMixin):
    """A customer's connected external file system (Google Drive / OneDrive /
    Dropbox / ...). OAuth is mocked for now; ``meta`` holds the (mock) token and
    a sample file listing. The real OAuth handshake fills these in later."""

    __tablename__ = "connections"

    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    display_name: Mapped[str] = mapped_column(String(255))
    account_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="connected")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditLog(Base, UUIDPkMixin, TimestampMixin):
    """Append-only trail of security-relevant customer actions (login, password
    reset, email verification, token-reuse, connection changes). ``detail`` never
    holds secret values."""

    __tablename__ = "audit_log"

    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class RevokedToken(Base, UUIDPkMixin, TimestampMixin):
    """Denylist of revoked JWT ids (jti). Refresh tokens are revoked on logout and
    rotated on use; an access token's short TTL bounds its window."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[int] = mapped_column(BigInteger, default=0)  # token exp (epoch seconds)
    reason: Mapped[str] = mapped_column(String(50), default="revoked")
    # The token family this jti belongs to. Reuse of a rotated refresh token
    # revokes the whole family (all descendants), not just the presented token.
    family_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class BillingRun(Base, UUIDPkMixin, TimestampMixin):
    """One billing attempt per (customer, period) — the idempotency guard that
    prevents double-charging. A period is a calendar month ("YYYY-MM"); once a run
    with an invoice exists for it, re-invoicing returns that run instead of charging
    again. ``line_items`` records the per-stack breakdown that was billed."""

    __tablename__ = "billing_runs"
    __table_args__ = (UniqueConstraint("customer_id", "period", name="uq_billing_run_customer_period"),)

    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)  # "YYYY-MM"
    plan_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="usd")
    invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="created")
    line_items: Mapped[list] = mapped_column(JSON, default=list)
