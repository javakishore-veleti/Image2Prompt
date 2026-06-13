"""add connections table

Creates the new table from model metadata (idempotent — existing tables are
skipped). Future changes should be explicit migrations.

Revision ID: 0002_connections
Revises: 0001_initial
Create Date: 2026-06-13
"""
from __future__ import annotations

from alembic import op

revision = "0002_connections"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import Connection

    Connection.__table__.drop(op.get_bind(), checkfirst=True)
