from __future__ import annotations

from sqlalchemy import JSON, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from image2prompt_shared.base import TimestampMixin, UUIDPkMixin

from .db import Base


class KbGroup(Base, UUIDPkMixin, TimestampMixin):
    """A project's Knowledge-Bank group: the container under a project that holds
    one or more Project KBs (one per tech-stack configuration)."""

    __tablename__ = "kb_groups"

    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(255))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class ProjectKb(Base, UUIDPkMixin, TimestampMixin):
    """A single Project KB inside a group, backed by one vector-store tech stack.
    Built incrementally from selected Image2Prompt generations."""

    __tablename__ = "project_kbs"

    group_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(255))
    tech_stack: Mapped[str] = mapped_column(String(50))  # pgvector | chroma | bedrock | ...
    status: Mapped[str] = mapped_column(String(50), default="active")
    doc_count: Mapped[int] = mapped_column(BigInteger, default=0)
    backend_ready: Mapped[bool] = mapped_column(default=False, server_default="0")
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class KbDocument(Base, UUIDPkMixin, TimestampMixin):
    """An ingested generation in a Project KB (the vector lives in the backing
    store; this row is the catalog entry + dedupe key)."""

    __tablename__ = "kb_documents"

    kb_id: Mapped[str] = mapped_column(String(36), index=True)
    generation_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class KbVector(Base, UUIDPkMixin, TimestampMixin):
    """SQL-backed vector index — the real, persistent store used by the pgvector
    stack (and the graceful fallback for any stack whose external backend isn't
    configured). Vector kept as JSON; cosine ranking done in the store."""

    __tablename__ = "kb_vectors"

    kb_id: Mapped[str] = mapped_column(String(36), index=True)
    doc_id: Mapped[str] = mapped_column(String(64), index=True)
    vector: Mapped[list] = mapped_column(JSON)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class KbIngestJob(Base, UUIDPkMixin, TimestampMixin):
    """An async ingestion job: embedding + fan-out runs in the background so large
    batches don't block the request. Clients poll it for progress."""

    __tablename__ = "kb_ingest_jobs"

    kb_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|error
    requested_ids: Mapped[list] = mapped_column(JSON, default=list)
    requested: Mapped[int] = mapped_column(BigInteger, default=0)
    ingested: Mapped[int] = mapped_column(BigInteger, default=0)
    skipped: Mapped[int] = mapped_column(BigInteger, default=0)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
