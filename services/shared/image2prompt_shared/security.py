"""Password hashing (bcrypt) and JWT encode/decode.

The JWT carries ``sub`` (subject id), ``typ`` ("customer" | "admin"), and
``email``. Services that verify tokens must share ``jwt_secret``/``jwt_algorithm``.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

import bcrypt
import jwt

from .base import utcnow

# bcrypt rejects inputs longer than 72 bytes.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    subject: str,
    token_type: str,
    email: str,
    secret: str,
    algorithm: str = "HS256",
    expire_minutes: int = 60 * 24,
    extra: dict[str, Any] | None = None,
) -> str:
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": subject,
        "typ": token_type,
        "email": email,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=algorithm)


def create_refresh_token(
    *,
    subject: str,
    email: str,
    secret: str,
    algorithm: str = "HS256",
    expire_minutes: int = 60 * 24 * 30,
    extra: dict[str, Any] | None = None,
) -> str:
    """A long-lived token of type 'refresh' used only to mint new access tokens."""
    return create_access_token(
        subject=subject,
        token_type="refresh",
        email=email,
        secret=secret,
        algorithm=algorithm,
        expire_minutes=expire_minutes,
        extra=extra,
    )


def decode_token(token: str, *, secret: str, algorithm: str = "HS256") -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``jwt.PyJWTError`` on failure."""
    return jwt.decode(token, secret, algorithms=[algorithm])
