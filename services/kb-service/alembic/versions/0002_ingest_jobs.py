"""add kb_ingest_jobs table (async ingestion)

Creates the new table from model metadata (idempotent — existing tables skipped).

Revision ID: 0002_ingest_jobs
Revises: 0001_initial
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op

revision = "0002_ingest_jobs"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import KbIngestJob

    KbIngestJob.__table__.drop(op.get_bind(), checkfirst=True)
