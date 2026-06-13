"""Local filesystem storage backend (the slice default)."""

from __future__ import annotations

import os

from .base import StorageBackend, StoredObject


class LocalStorage(StorageBackend):
    name = "local"

    def __init__(self, base_dir: str = "/data/uploads") -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _abspath(self, key: str) -> str:
        # Keys may contain a subdir (e.g. "<customer_id>/<uuid>.png").
        safe = key.lstrip("/")
        return os.path.join(self.base_dir, safe)

    def save(self, data: bytes, *, key: str, content_type: str) -> StoredObject:
        path = self._abspath(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return StoredObject(
            backend=self.name,
            location=key,
            content_type=content_type,
            size=len(data),
        )

    def load(self, location: str) -> bytes:
        with open(self._abspath(location), "rb") as fh:
            return fh.read()
