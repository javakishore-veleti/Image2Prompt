"""Symmetric encryption for secrets at rest (e.g. stored OAuth tokens).

Feature-toggled and fail-safe, in the spirit of the rest of the shared lib:
- If no key is configured, the cipher is *disabled* and ``encrypt``/``decrypt``
  pass the value through unchanged (``enabled`` is False).
- If the ``cryptography`` package is missing, the cipher is also disabled.
- ``decrypt`` never raises: an undecryptable value (wrong key / corrupt) returns
  an empty string so callers degrade to a normal "no token" path rather than
  crashing or leaking ciphertext to a provider.

Key rotation: pass one or more ``previous_keys``. Decryption tries the current
key first, then each previous key (via Fernet's MultiFernet), so changing
``TOKEN_ENCRYPTION_KEY`` doesn't orphan existing data. New values are always
written under the current (first) key; ``rotate`` re-seals a value under it so
old keys can eventually be retired.

Ciphertext is tagged with a short version prefix (``enc:v1:``) so we can tell an
encrypted value from a legacy plaintext one and migrate transparently.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Iterable

_PREFIX = "enc:v1:"


class TokenCipher:
    """Fernet-based AES-128-CBC + HMAC cipher keyed from arbitrary secret(s).

    Each provided key string can be any length/charset; it is hashed to a valid
    32-byte url-safe key, so operators can reuse a passphrase-style secret.
    """

    def __init__(self, key: str | None, *, previous_keys: Iterable[str] | None = None) -> None:
        self._multi = None  # MultiFernet: encrypt with current, decrypt with any
        raw_keys = [key, *(previous_keys or [])]
        keys = [k for k in raw_keys if k]
        if not keys:
            return
        try:
            from cryptography.fernet import Fernet, MultiFernet

            self._multi = MultiFernet([Fernet(self._derive(k)) for k in keys])
        except Exception:  # missing package or bad key -> stay disabled, never raise
            self._multi = None

    @staticmethod
    def _derive(key: str) -> bytes:
        return base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest())

    @property
    def enabled(self) -> bool:
        return self._multi is not None

    def encrypt(self, plaintext: str) -> str:
        """Return ``enc:v1:<token>`` under the current key; pass through unchanged
        when disabled/empty."""
        if not plaintext or not self._multi:
            return plaintext
        token = self._multi.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        return f"{_PREFIX}{token}"

    def decrypt(self, value: str) -> str:
        """Inverse of ``encrypt``, trying the current then previous keys. Plaintext
        (untagged) values pass through; returns "" for an unrecoverable value."""
        if not value or not value.startswith(_PREFIX):
            return value  # legacy plaintext or empty
        if not self._multi:
            return ""  # tagged but we have no key -> cannot recover
        try:
            return self._multi.decrypt(value[len(_PREFIX):].encode("utf-8")).decode("utf-8")
        except Exception:
            return ""

    def rotate(self, value: str) -> str:
        """Re-seal a tagged value under the current key (decrypt-then-encrypt).

        Returns the value unchanged if it isn't decryptable or encryption is off.
        Used by the re-encryption maintenance path after a key change.
        """
        if not self.is_encrypted(value) or not self._multi:
            return value
        plain = self.decrypt(value)
        if not plain:
            return value  # couldn't recover (e.g. retired key) — leave as-is
        return self.encrypt(plain)

    @staticmethod
    def is_encrypted(value: str) -> bool:
        return bool(value) and value.startswith(_PREFIX)
