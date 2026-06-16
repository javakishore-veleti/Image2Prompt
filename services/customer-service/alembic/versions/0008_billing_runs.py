"""add billing_runs table (billing idempotency)

Creates the new table from model metadata (idempotent — existing tables skipped).

Revision ID: 0008_billing_runs
Revises: 0007_audit_immutable
Create Date: 2026-06-15
"""
from __future__ import annotations

from alembic import op

revision = "0008_billing_runs"
down_revision = "0007_audit_immutable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import BillingRun

    BillingRun.__table__.drop(op.get_bind(), checkfirst=True)
