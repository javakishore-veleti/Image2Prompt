"""FastAPI auth dependencies that decode the bearer JWT into a principal.

Services build their own dependencies from these factories so they can inject
their own ``jwt_secret`` without a global. Example::

    from image2prompt_shared.auth_dep import make_principal_dep
    current_customer = make_principal_dep(settings, required_type="customer")
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .security import decode_token

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    id: str
    type: str  # "customer" | "admin"
    email: str
    claims: dict


def make_principal_dep(settings, *, required_type: str | None = None):
    """Return a FastAPI dependency that yields a verified ``Principal``."""

    def _dep(
        creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> Principal:
        if creds is None or not creds.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        try:
            payload = decode_token(
                creds.credentials,
                secret=settings.jwt_secret,
                algorithm=settings.jwt_algorithm,
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        principal = Principal(
            id=payload.get("sub", ""),
            type=payload.get("typ", ""),
            email=payload.get("email", ""),
            claims=payload,
        )
        if required_type and principal.type != required_type:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_type} privileges",
            )
        return principal

    return _dep


def make_role_dep(settings, *, required_type: str, roles: set[str]):
    """Like make_principal_dep, but also requires the principal's ``role`` claim
    to be one of ``roles`` (403 otherwise). For RBAC on specific endpoints."""

    base = make_principal_dep(settings, required_type=required_type)

    def _dep(principal: Principal = Depends(base)) -> Principal:
        if principal.claims.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {sorted(roles)}",
            )
        return principal

    return _dep
