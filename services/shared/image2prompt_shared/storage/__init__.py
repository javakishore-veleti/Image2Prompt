"""Pluggable storage backends.

The active backend is chosen per customer preference / service config:
``local`` (filesystem), ``s3``, ``azure``, ``gcp`` — all real. Cloud backends
lazily import their SDK and read config from kwargs (passed from settings) with
env fallbacks.
"""

from .base import StorageBackend, StoredObject
from .cloud import AzureBlobStorage, GCPBlobStorage, S3Storage
from .local import LocalStorage


def get_storage_backend(name: str, **cfg) -> StorageBackend:
    name = (name or "local").lower()
    if name == "local":
        return LocalStorage(base_dir=cfg.get("base_dir", "/data/uploads"))
    if name in ("s3", "aws"):
        return S3Storage(
            bucket=cfg.get("s3_bucket"), prefix=cfg.get("s3_prefix"), region=cfg.get("region")
        )
    if name in ("azure", "azure_blob"):
        return AzureBlobStorage(
            container=cfg.get("azure_blob_container"),
            connection_string=cfg.get("azure_storage_connection_string"),
            account_url=cfg.get("azure_storage_account_url"),
        )
    if name in ("gcp", "gcs", "gcp_blob"):
        return GCPBlobStorage(bucket=cfg.get("gcs_bucket"), prefix=cfg.get("gcs_prefix"))
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
