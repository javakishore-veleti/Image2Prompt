"""Storage backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoredObject:
    backend: str        # "local" | "s3" | "azure" | "gcp"
    location: str       # backend-specific key/path used to fetch the bytes later
    content_type: str
    size: int


class StorageBackend(ABC):
    name: str = "abstract"

    @abstractmethod
    def save(self, data: bytes, *, key: str, content_type: str) -> StoredObject:
        """Persist ``data`` under ``key`` and return a reference to it."""

    @abstractmethod
    def load(self, location: str) -> bytes:
        """Return the bytes previously stored at ``location``."""
