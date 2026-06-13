"""Per-service SQLAlchemy engine/session factory + schema/migration bootstrap.

Usage::

    from image2prompt_shared.db import Database
    db = Database(settings.database_url, schema=settings.db_schema)
    db.bootstrap(base=Base, settings=settings, service_dir=HERE, seed_fn=seed)

    def get_db():           # FastAPI dependency
        yield from db.session()
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Callable

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .logging_config import get_logger

log = get_logger(__name__)


class Database:
    def __init__(self, database_url: str, *, schema: str | None = None) -> None:
        self.database_url = database_url
        self.schema = schema if schema and schema != "public" else None
        self.is_sqlite = database_url.startswith("sqlite")
        self.engine = create_engine(database_url, pool_pre_ping=True, future=True)
        self.SessionLocal = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False, future=True
        )

    def ensure_schema(self) -> None:
        """Create the service schema if it doesn't exist (Postgres only)."""
        if self.is_sqlite or not self.schema:
            return
        with self.engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"'))
            log.info("db: ensured schema %s", self.schema)

    def create_all(self, base) -> None:
        base.metadata.create_all(bind=self.engine)

    def bootstrap(
        self,
        *,
        base,
        settings,
        service_dir: str | None = None,
        seed_fn: Callable[[Session], None] | None = None,
    ) -> None:
        """Ensure schema, apply migrations (Alembic on Postgres; create_all on
        SQLite/when migrations are off), then run an idempotent seed."""
        self.ensure_schema()
        migrated = False
        if (
            not self.is_sqlite
            and getattr(settings, "run_migrations_on_startup", True)
            and service_dir
            and os.path.exists(os.path.join(service_dir, "alembic.ini"))
        ):
            migrated = self._alembic_upgrade(service_dir)
        if not migrated:
            self.create_all(base)
        if seed_fn:
            with self.SessionLocal() as session:
                seed_fn(session)

    def _alembic_upgrade(self, service_dir: str) -> bool:
        try:
            from alembic import command
            from alembic.config import Config

            cfg = Config(os.path.join(service_dir, "alembic.ini"))
            cfg.set_main_option("script_location", os.path.join(service_dir, "alembic"))
            cfg.set_main_option("sqlalchemy.url", self.database_url)
            command.upgrade(cfg, "head")
            log.info("db: alembic upgrade head complete")
            return True
        except Exception as exc:
            log.warning("db: alembic upgrade failed (%s); falling back to create_all", exc)
            return False

    def session(self) -> Iterator[Session]:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
