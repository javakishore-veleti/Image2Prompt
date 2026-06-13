"""add csp_violations table

Creates the new table from model metadata (idempotent — existing tables skipped).

Revision ID: 0003_csp_violations
Revises: 0002_revoked_tokens
Create Date: 2026-06-13
"""
from __future__ import annotations

from alembic import op

revision = "0003_csp_violations"
down_revision = "0002_revoked_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import CspViolation

    CspViolation.__table__.drop(op.get_bind(), checkfirst=True)
