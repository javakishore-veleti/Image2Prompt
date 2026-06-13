from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from image2prompt_shared.base import Base, TimestampMixin, UUIDPkMixin


class FileRef(Base, UUIDPkMixin, TimestampMixin):
    """A stored upload. The id is the reference used everywhere else."""

    __tablename__ = "file_refs"

    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    backend: Mapped[str] = mapped_column(String(50), default="local")
    location: Mapped[str] = mapped_column(String(1024))
    content_type: Mapped[str] = mapped_column(String(255), default="application/octet-stream")
    size: Mapped[int] = mapped_column(Integer, default=0)
    # ``meta`` maps to a JSON column named "metadata" (SQLAlchemy reserves the
    # attribute name ``metadata`` on declarative classes).
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class ProcReqLog(Base, UUIDPkMixin, TimestampMixin):
    """One image-processing request. ``id`` is the request id referenced by
    each provider response row."""

    __tablename__ = "proc_req_log"

    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    file_ref_id: Mapped[str] = mapped_column(String(36), index=True)
    instruction: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    requested_providers: Mapped[list] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    providers: Mapped[list["ProcReqLogProvider"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class ProcReqLogProvider(Base, UUIDPkMixin, TimestampMixin):
    """The result of dispatching one request to one provider."""

    __tablename__ = "proc_req_log_providers"

    proc_req_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("proc_req_log.id", ondelete="CASCADE"), index=True
    )
    provider_key: Mapped[str] = mapped_column(String(100), index=True)
    provider_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    response_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    request: Mapped["ProcReqLog"] = relationship(back_populates="providers")
