"""add subscription_plans + customer_subscriptions

Creates the new tables from model metadata (idempotent — existing tables skipped).

Revision ID: 0007_subscriptions
Revises: 0006_audit_immutable
Create Date: 2026-06-14
"""
from __future__ import annotations

from alembic import op

revision = "0007_subscriptions"
down_revision = "0006_audit_immutable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.db import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import CustomerSubscription, SubscriptionPlan

    CustomerSubscription.__table__.drop(op.get_bind(), checkfirst=True)
    SubscriptionPlan.__table__.drop(op.get_bind(), checkfirst=True)
