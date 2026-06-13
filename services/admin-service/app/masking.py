"""Mask secret-looking values in provider config for admin-facing responses.

The DB stores config encrypted at rest, but a decrypted config still contains
real API keys. Admin UIs don't need the raw secret — they need to know one is
set. So `GET /admin/providers` returns secret values replaced with MASK, while
the internal endpoint (consumed by image-processing) returns the real values.

To let admins edit non-secret fields without wiping secrets, `merge_with_existing`
treats any incoming value equal to MASK as "unchanged" and restores the stored value.
"""

from __future__ import annotations

MASK = "••••••••"  # ••••••••

# A config key is treated as secret if its name contains any of these.
_SECRET_HINTS = ("secret", "key", "token", "password", "pwd", "credential", "passwd")


def is_secret_key(name: str) -> bool:
    lowered = name.lower()
    return any(h in lowered for h in _SECRET_HINTS)


def mask_config(config: dict | None) -> dict:
    """Replace non-empty secret string values with MASK; leave the rest as-is."""
    out: dict = {}
    for k, v in (config or {}).items():
        if is_secret_key(k) and isinstance(v, str) and v:
            out[k] = MASK
        else:
            out[k] = v
    return out


def merge_with_existing(incoming: dict | None, existing: dict | None) -> dict:
    """Build the config to persist: any incoming value equal to MASK is a
    placeholder for an unchanged secret and is replaced by the existing value."""
    existing = existing or {}
    merged: dict = {}
    for k, v in (incoming or {}).items():
        if v == MASK and k in existing:
            merged[k] = existing[k]
        else:
            merged[k] = v
    return merged
