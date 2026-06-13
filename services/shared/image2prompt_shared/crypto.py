"""Symmetric encryption for secrets at rest (e.g. stored OAuth tokens).

Feature-toggled and fail-safe, in the spirit of the rest of the shared lib:
- If no key is configured, the cipher is *disabled* and ``encrypt``/``decrypt``
  pass the value through unchanged (``enabled`` is False).
- If the ``cryptography`` package is missing, the cipher is also disabled.
- ``decrypt`` never raises: an undecryptable value (wrong key / corrupt) returns
  an empty string so callers degrade to a normal "no token" path rather than
  crashing or leaking ciphertext to a provider.

Ciphertext is tagged with a short version prefix (``enc:v1:``) so we can tell an
encrypted value from a legacy plaintext one and migrate transparently.
"""

from __future__ import annotations

import base64
import hashlib

_PREFIX = "enc:v1:"


class TokenCipher:
    """Fernet-based AES-128-CBC + HMAC cipher keyed from an arbitrary secret.

    The provided key string can be any length/charset; it is hashed to a valid
    32-byte url-safe key, so operators can reuse a passphrase-style secret.
    """

    def __init__(self, key: str | None) -> None:
        self._fernet = None
        if not key:
            return
        try:
            from cryptography.fernet import Fernet

            derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest())
            self._fernet = Fernet(derived)
        except Exception:  # missing package or bad key -> stay disabled, never raise
            self._fernet = None

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        """Return ``enc:v1:<token>``; pass through unchanged when disabled/empty."""
        if not plaintext or not self._fernet:
            return plaintext
        token = self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        return f"{_PREFIX}{token}"

    def decrypt(self, value: str) -> str:
        """Inverse of ``encrypt``. Plaintext (untagged) values pass through.

        Returns "" if a tagged value can't be decrypted (wrong/rotated key).
        """
        if not value or not value.startswith(_PREFIX):
            return value  # legacy plaintext or empty
        if not self._fernet:
            return ""  # tagged but we have no key -> cannot recover
        try:
            return self._fernet.decrypt(value[len(_PREFIX):].encode("utf-8")).decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def is_encrypted(value: str) -> bool:
        return bool(value) and value.startswith(_PREFIX)
