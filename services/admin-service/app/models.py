from __future__ import annotations

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from image2prompt_shared.base import Base, TimestampMixin, UUIDPkMixin


class AdminUser(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="admin")


class Provider(Base, UUIDPkMixin, TimestampMixin):
    """An AI provider the platform can dispatch process requests to.

    ``key`` is the stable identifier shared with the ai-adapters registry
    (bedrock, anthropic, openai, ...). ``enabled`` is the global on/off switch
    admins control. ``config`` holds arbitrary provider settings as JSON.
    """

    __tablename__ = "providers"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), default="generic")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
