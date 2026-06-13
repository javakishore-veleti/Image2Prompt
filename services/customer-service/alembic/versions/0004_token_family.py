"""add family_id to revoked_tokens (token-family revocation)

Idempotent: on a fresh DB 0001's metadata create_all already includes the column,
so we add it only when missing (existing deployments).

Revision ID: 0004_token_family
Revises: 0003_revoked_tokens
Create Date: 2026-06-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_token_family"
down_revision = "0003_revoked_tokens"
branch_labels = None
depends_on = None

_TABLE = "revoked_tokens"
_COL = "family_id"


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
        op.add_column(_TABLE, sa.Column(_COL, sa.String(length=36), nullable=True), schema=schema)
        op.create_index(
            f"ix_{_TABLE}_{_COL}", _TABLE, [_COL], unique=False, schema=schema
        )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema() if bind.dialect.name != "sqlite" else None
    if _has_column(bind, schema):
        op.drop_index(f"ix_{_TABLE}_{_COL}", table_name=_TABLE, schema=schema)
        op.drop_column(_TABLE, _COL, schema=schema)
