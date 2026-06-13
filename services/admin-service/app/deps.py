from __future__ import annotations

from image2prompt_shared.auth_dep import make_principal_dep, make_role_dep

from .config import settings
from .db import get_db  # re-exported for controllers

# Roles (broadest -> narrowest): superadmin > admin > viewer.
WRITE_ROLES = {"admin", "superadmin"}

# Any authenticated admin (read access).
current_admin = make_principal_dep(settings, required_type="admin")
# Mutating actions require admin or superadmin (viewer is read-only).
admin_writer = make_role_dep(settings, required_type="admin", roles=WRITE_ROLES)

__all__ = ["get_db", "current_admin", "admin_writer"]
