from __future__ import annotations

from image2prompt_shared.auth_dep import make_principal_dep
from image2prompt_shared.db import Database

from .config import settings

db = Database(settings.database_url)


def get_db():
    yield from db.session()


current_customer = make_principal_dep(settings, required_type="customer")
