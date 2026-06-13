"""Pluggable storage backends.

The active backend is chosen per customer preference / service config. The slice
implements ``local``; S3/Azure/GCP are registered stubs that raise until built.
"""

from .base import StorageBackend, StoredObject
from .local import LocalStorage
from .stubs import AzureBlobStorage, GCPBlobStorage, S3Storage


def get_storage_backend(name: str, **kwargs) -> StorageBackend:
    name = (name or "local").lower()
    if name == "local":
        return LocalStorage(base_dir=kwargs.get("base_dir", "/data/uploads"))
    if name in ("s3", "aws"):
        return S3Storage(**kwargs)
    if name in ("azure", "azure_blob"):
        return AzureBlobStorage(**kwargs)
    if name in ("gcp", "gcs", "gcp_blob"):
        return GCPBlobStorage(**kwargs)
    raise ValueError(f"Unknown storage backend: {name!r}")


__all__ = [
    "StorageBackend",
    "StoredObject",
    "LocalStorage",
    "S3Storage",
    "AzureBlobStorage",
    "GCPBlobStorage",
    "get_storage_backend",
]
