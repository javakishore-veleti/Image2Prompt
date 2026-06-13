"""Cloud storage backends — registered but not yet implemented.

These keep the interface and wiring in place so a customer's ``storage_backend``
preference (s3 / azure / gcp) is a config change, not a code change, once the
real SDK calls are filled in.
"""

from __future__ import annotations

from .base import StorageBackend, StoredObject


class _NotImplementedStorage(StorageBackend):
    def __init__(self, **kwargs) -> None:
        self.config = kwargs

    def save(self, data: bytes, *, key: str, content_type: str) -> StoredObject:
        raise NotImplementedError(f"{self.name} storage backend is not implemented yet")

    def load(self, location: str) -> bytes:
        raise NotImplementedError(f"{self.name} storage backend is not implemented yet")


class S3Storage(_NotImplementedStorage):
    name = "s3"


class AzureBlobStorage(_NotImplementedStorage):
    name = "azure"


class GCPBlobStorage(_NotImplementedStorage):
    name = "gcp"
