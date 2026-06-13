"""make audit_log append-only at the DB level (Postgres)

Installs a trigger that rejects UPDATE/DELETE on audit_log so the trail is
tamper-evident even to the application role. No-op on SQLite (tests); the
application never updates/deletes audit rows anyway.

Revision ID: 0006_audit_immutable
Revises: 0005_audit_log
Create Date: 2026-06-13
"""
from __future__ import annotations

from alembic import op

revision = "0006_audit_immutable"
down_revision = "0005_audit_log"
branch_labels = None
depends_on = None


def _table() -> str:
    from app.db import Base

    schema = Base.metadata.schema
    return f'"{schema}".audit_log' if schema else "audit_log"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    tbl = _table()
    op.execute(
        """
        CREATE OR REPLACE FUNCTION img2pmpt_audit_immutable()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(f"DROP TRIGGER IF EXISTS audit_no_update ON {tbl};")
    op.execute(f"DROP TRIGGER IF EXISTS audit_no_delete ON {tbl};")
    op.execute(
        f"CREATE TRIGGER audit_no_update BEFORE UPDATE ON {tbl} "
        f"FOR EACH ROW EXECUTE FUNCTION img2pmpt_audit_immutable();"
    )
    op.execute(
        f"CREATE TRIGGER audit_no_delete BEFORE DELETE ON {tbl} "
        f"FOR EACH ROW EXECUTE FUNCTION img2pmpt_audit_immutable();"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    tbl = _table()
    op.execute(f"DROP TRIGGER IF EXISTS audit_no_update ON {tbl};")
    op.execute(f"DROP TRIGGER IF EXISTS audit_no_delete ON {tbl};")
    op.execute("DROP FUNCTION IF EXISTS img2pmpt_audit_immutable();")
