"""add email_verified to customers

Idempotent: on a fresh DB 0001's metadata create_all already includes the column,
so we add it only when missing (existing deployments).

Revision ID: 0005_email_verified
Revises: 0004_token_family
Create Date: 2026-06-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_email_verified"
down_revision = "0004_token_family"
branch_labels = None
depends_on = None

_TABLE = "customers"
_COL = "email_verified"


def _schema():
    from app.db import Base

    return Base.metadata.schema


def _has_column(bind, schema) -> bool:
    insp = sa.inspect(bind)
    return any(c["name"] == _COL for c in insp.get_columns(_TABLE, schema=schema))


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema() if bind.dialect.name != "sqlite" else None
    if not _has_column(bind, schema):
        op.add_column(
            _TABLE,
            sa.Column(_COL, sa.Boolean(), nullable=False, server_default=sa.text("false")),
            schema=schema,
        )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema() if bind.dialect.name != "sqlite" else None
    if _has_column(bind, schema):
        op.drop_column(_TABLE, _COL, schema=schema)
