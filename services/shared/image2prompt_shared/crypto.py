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
written under the current (first) key; ``rotate`` re-seals a value under it.

Key versioning: ciphertext is tagged ``enc:v2:<kid>:<token>`` where ``kid`` is a
short fingerprint of the encrypting key. This lets callers tell which key a value
is under (``is_current``) and report rotation progress. Legacy ``enc:v1:<token>``
(no kid) and plaintext are still read transparently and count as "not current".
"""

from __future__ import annotations

import base64
import hashlib
from typing import Iterable, Optional

_PREFIX_V1 = "enc:v1:"
_PREFIX_V2 = "enc:v2:"  # enc:v2:<kid>:<fernet-token>


class TokenCipher:
    """Fernet-based AES-128-CBC + HMAC cipher keyed from arbitrary secret(s)."""

    def __init__(self, key: str | None, *, previous_keys: Iterable[str] | None = None) -> None:
        self._multi = None  # MultiFernet: encrypt with current, decrypt with any
        self._kid: Optional[str] = None
        raw_keys = [key, *(previous_keys or [])]
        keys = [k for k in raw_keys if k]
        if not keys:
            return
        try:
            from cryptography.fernet import Fernet, MultiFernet

            self._multi = MultiFernet([Fernet(self._derive(k)) for k in keys])
            self._kid = self.fingerprint(key) if key else None
        except Exception:  # missing package or bad key -> stay disabled, never raise
            self._multi = None
            self._kid = None

    @staticmethod
    def _derive(key: str) -> bytes:
        return base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest())

    @staticmethod
    def fingerprint(key: str) -> str:
        """Short, non-reversible id for a key (for ciphertext tagging / reporting)."""
        return hashlib.sha256(("kid:" + key).encode("utf-8")).hexdigest()[:12]

    @property
    def enabled(self) -> bool:
        return self._multi is not None

    @property
    def current_key_id(self) -> Optional[str]:
        return self._kid

    def encrypt(self, plaintext: str) -> str:
        """Return ``enc:v2:<kid>:<token>`` under the current key; pass through
        unchanged when disabled/empty."""
        if not plaintext or not self._multi:
            return plaintext
        token = self._multi.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        return f"{_PREFIX_V2}{self._kid}:{token}"

    def decrypt(self, value: str) -> str:
        """Inverse of ``encrypt`` (handles v1 + v2), trying current then previous
        keys. Plaintext passes through; returns "" for an unrecoverable value."""
        token = self._strip(value)
        if token is None:
            return value  # legacy plaintext or empty
        if not self._multi:
            return ""  # tagged but we have no key -> cannot recover
        try:
            return self._multi.decrypt(token.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""

    def rotate(self, value: str) -> str:
        """Re-seal a tagged value under the current key (decrypt-then-encrypt).

        Returns the value unchanged if it isn't decryptable or encryption is off.
        """
        if not self.is_encrypted(value) or not self._multi:
            return value
        plain = self.decrypt(value)
        if not plain:
            return value  # couldn't recover (e.g. retired key) — leave as-is
        return self.encrypt(plain)

    def is_current(self, value: str) -> bool:
        """True if ``value`` is encrypted under this cipher's current key id."""
        return self._kid is not None and self.key_id(value) == self._kid

    # --- format helpers -------------------------------------------------------
    @staticmethod
    def _strip(value: str) -> Optional[str]:
        """Return the raw fernet token from a tagged value, or None if untagged."""
        if not value:
            return None
        if value.startswith(_PREFIX_V2):
            _, _, token = value[len(_PREFIX_V2):].partition(":")
            return token
        if value.startswith(_PREFIX_V1):
            return value[len(_PREFIX_V1):]
        return None

    @staticmethod
    def is_encrypted(value: str) -> bool:
        return bool(value) and (value.startswith(_PREFIX_V1) or value.startswith(_PREFIX_V2))

    @staticmethod
    def key_id(value: str) -> Optional[str]:
        """The key id a value was sealed with (v2 only); None for v1/plaintext."""
        if value and value.startswith(_PREFIX_V2):
            kid, _, _ = value[len(_PREFIX_V2):].partition(":")
            return kid or None
        return None
