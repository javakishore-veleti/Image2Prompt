"""add fingerprint + count to csp_violations (dedupe)

Idempotent: on a fresh DB 0003's create_all already includes the columns, so we
add them only when missing (existing deployments).

Revision ID: 0004_csp_dedupe
Revises: 0003_csp_violations
Create Date: 2026-06-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_csp_dedupe"
down_revision = "0003_csp_violations"
branch_labels = None
depends_on = None

_TABLE = "csp_violations"


def _schema():
    from app.db import Base

    return Base.metadata.schema


def _has_column(bind, schema, col) -> bool:
    insp = sa.inspect(bind)
    return any(c["name"] == col for c in insp.get_columns(_TABLE, schema=schema))


def upgrade() -> None:
    bind = op.get_bind()
    schema = _schema() if bind.dialect.name != "sqlite" else None
    if not _has_column(bind, schema, "fingerprint"):
        op.add_column(_TABLE, sa.Column("fingerprint", sa.String(length=64), nullable=True), schema=schema)
        op.create_index(f"ix_{_TABLE}_fingerprint", _TABLE, ["fingerprint"], schema=schema)
    if not _has_column(bind, schema, "count"):
        op.add_column(
            _TABLE,
            sa.Column("count", sa.BigInteger(), nullable=False, server_default="1"),
            schema=schema,
        )


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema() if bind.dialect.name != "sqlite" else None
    if _has_column(bind, schema, "count"):
        op.drop_column(_TABLE, "count", schema=schema)
    if _has_column(bind, schema, "fingerprint"):
        op.drop_index(f"ix_{_TABLE}_fingerprint", table_name=_TABLE, schema=schema)
        op.drop_column(_TABLE, "fingerprint", schema=schema)
