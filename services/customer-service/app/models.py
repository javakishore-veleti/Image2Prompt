from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from image2prompt_shared.base import TimestampMixin, UUIDPkMixin

from .db import Base


class Customer(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "customers"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")


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
