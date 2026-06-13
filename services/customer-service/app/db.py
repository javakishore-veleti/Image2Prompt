from __future__ import annotations

from image2prompt_shared.base import build_base
from image2prompt_shared.db import Database

from .config import settings

# Postgres uses the per-service schema; SQLite (tests) has no schema support.
_schema = None if settings.is_sqlite else settings.db_schema

Base = build_base(_schema)
db = Database(settings.database_url, schema=_schema)


def get_db():
    yield from db.session()
