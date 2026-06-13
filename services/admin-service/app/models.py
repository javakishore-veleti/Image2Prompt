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
