"""Per-service SQLAlchemy engine/session factory.

Usage in a service::

    from image2prompt_shared.db import Database
    db = Database(settings.database_url)
    db.create_all(Base)              # at startup (slice: no Alembic yet)

    def get_db():                    # FastAPI dependency
        yield from db.session()
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True, future=True)
        self.SessionLocal = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False, future=True
        )

    def create_all(self, base) -> None:
        base.metadata.create_all(bind=self.engine)

    def session(self) -> Iterator[Session]:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
