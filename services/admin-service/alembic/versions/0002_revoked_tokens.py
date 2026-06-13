"""add revoked_tokens table

Revision ID: 0002_revoked_tokens
Revises: 0001_initial
Create Date: 2026-06-13
"""
from __future__ import annotations

from alembic import op

revision = "0002_revoked_tokens"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import RevokedToken

    RevokedToken.__table__.drop(op.get_bind(), checkfirst=True)
