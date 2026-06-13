"""SQLAlchemy declarative base, schema-scoped base factory, and column mixins."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Default declarative base (schema = public)."""


def build_base(schema: str | None) -> type[DeclarativeBase]:
    """Return a fresh declarative base whose tables live in ``schema``.

    Each service builds its own base bound to its ``img2pmpt_*`` schema so the
    schema is scoped per service (and SQLite tests can pass schema=None).
    """
    meta = MetaData(schema=schema or None)

    class _ScopedBase(DeclarativeBase):
        metadata = meta

    return _ScopedBase


class UUIDPkMixin:
    """String UUID primary key (portable across services, JSON-friendly)."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utcnow,
        onupdate=utcnow,
    )
