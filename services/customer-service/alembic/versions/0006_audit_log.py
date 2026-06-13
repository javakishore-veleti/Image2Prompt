"""add audit_log table

Creates the new table from model metadata (idempotent — existing tables skipped).

Revision ID: 0006_audit_log
Revises: 0005_email_verified
Create Date: 2026-06-13
"""
from __future__ import annotations

from alembic import op

revision = "0006_audit_log"
down_revision = "0005_email_verified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import AuditLog

    AuditLog.__table__.drop(op.get_bind(), checkfirst=True)
