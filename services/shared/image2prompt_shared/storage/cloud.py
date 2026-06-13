"""Cloud storage backends — S3, Azure Blob, GCP Cloud Storage.

Each lazily imports its SDK and uses the default credential chain (boto3 default
creds / Azure connection-string or DefaultAzureCredential / GCP ADC). Config comes
from explicit kwargs (passed from settings) with env-var fallbacks. Missing
config raises ValueError; a missing SDK raises ImportError — callers treat both
as a storage failure rather than crashing.
"""

from __future__ import annotations

import os

from .base import StorageBackend, StoredObject


class S3Storage(StorageBackend):
    name = "s3"

    def __init__(self, *, bucket: str | None = None, prefix: str | None = None,
                 region: str | None = None, **_) -> None:
        self.bucket = bucket or os.environ.get("S3_BUCKET", "")
        self.prefix = (prefix or os.environ.get("S3_PREFIX", "uploads/")).strip("/")
        self.region = region or os.environ.get("AWS_REGION")

    def _client(self):
        import boto3

        return boto3.client("s3", region_name=self.region)

    def _full(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def save(self, data: bytes, *, key: str, content_type: str) -> StoredObject:
        if not self.bucket:
            raise ValueError("S3 storage requires S3_BUCKET")
        full = self._full(key)
        self._client().put_object(Bucket=self.bucket, Key=full, Body=data, ContentType=content_type)
        return StoredObject(backend=self.name, location=full, content_type=content_type, size=len(data))

    def load(self, location: str) -> bytes:
        return self._client().get_object(Bucket=self.bucket, Key=location)["Body"].read()


class AzureBlobStorage(StorageBackend):
    name = "azure"

    def __init__(self, *, container: str | None = None, connection_string: str | None = None,
                 account_url: str | None = None, **_) -> None:
        self.container = container or os.environ.get("AZURE_BLOB_CONTAINER", "")
        self.connection_string = connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
        self.account_url = account_url or os.environ.get("AZURE_STORAGE_ACCOUNT_URL", "")

    def _service(self):
        from azure.storage.blob import BlobServiceClient

        if self.connection_string:
            return BlobServiceClient.from_connection_string(self.connection_string)
        from azure.identity import DefaultAzureCredential

        return BlobServiceClient(account_url=self.account_url, credential=DefaultAzureCredential())

    def save(self, data: bytes, *, key: str, content_type: str) -> StoredObject:
        if not self.container or not (self.connection_string or self.account_url):
            raise ValueError("Azure storage requires AZURE_BLOB_CONTAINER and a connection string / account URL")
        from azure.storage.blob import ContentSettings

        client = self._service().get_blob_client(container=self.container, blob=key)
        client.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))
        return StoredObject(backend=self.name, location=key, content_type=content_type, size=len(data))

    def load(self, location: str) -> bytes:
        client = self._service().get_blob_client(container=self.container, blob=location)
        return client.download_blob().readall()


class GCPBlobStorage(StorageBackend):
    name = "gcp"

    def __init__(self, *, bucket: str | None = None, prefix: str | None = None, **_) -> None:
        self.bucket_name = bucket or os.environ.get("GCS_BUCKET", "")
        self.prefix = (prefix or os.environ.get("GCS_PREFIX", "uploads/")).strip("/")

    def _bucket(self):
        from google.cloud import storage

        return storage.Client().bucket(self.bucket_name)

    def _full(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def save(self, data: bytes, *, key: str, content_type: str) -> StoredObject:
        if not self.bucket_name:
            raise ValueError("GCP storage requires GCS_BUCKET")
        full = self._full(key)
        self._bucket().blob(full).upload_from_string(data, content_type=content_type)
        return StoredObject(backend=self.name, location=full, content_type=content_type, size=len(data))

    def load(self, location: str) -> bytes:
        return self._bucket().blob(location).download_as_bytes()
