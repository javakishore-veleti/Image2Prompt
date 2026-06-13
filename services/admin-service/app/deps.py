from __future__ import annotations

from image2prompt_shared.auth_dep import make_principal_dep

from .config import settings
from .db import get_db  # re-exported for controllers

current_admin = make_principal_dep(settings, required_type="admin")

__all__ = ["get_db", "current_admin"]
