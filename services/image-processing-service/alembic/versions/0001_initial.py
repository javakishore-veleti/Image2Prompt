"""initial image-processing-service schema

Creates the img2pmpt_image schema and all tables from the model metadata.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-12
"""
from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    bind = op.get_bind()
    schema = Base.metadata.schema
    if schema and bind.dialect.name != "sqlite":
        bind.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    Base.metadata.drop_all(op.get_bind())
