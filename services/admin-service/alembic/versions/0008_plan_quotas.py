"""add per-plan quota columns to subscription_plans

Adds max_kbs / max_docs_per_kb (NULL = unlimited). Idempotent: skips a column that
already exists (e.g. when create_all already built the table on a fresh DB).

Revision ID: 0008_plan_quotas
Revises: 0007_subscriptions
Create Date: 2026-06-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_plan_quotas"
down_revision = "0007_subscriptions"
branch_labels = None
depends_on = None


def _schema() -> str | None:
    from app.db import Base

    return Base.metadata.schema


def _existing_cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    try:
        return {c["name"] for c in insp.get_columns(table, schema=_schema())}
    except Exception:
        return set()


def upgrade() -> None:
    cols = _existing_cols("subscription_plans")
    for name in ("max_kbs", "max_docs_per_kb"):
        if name not in cols:
            op.add_column(
                "subscription_plans",
                sa.Column(name, sa.BigInteger(), nullable=True),
                schema=_schema(),
            )


def downgrade() -> None:
    for name in ("max_docs_per_kb", "max_kbs"):
        op.drop_column("subscription_plans", name, schema=_schema())
