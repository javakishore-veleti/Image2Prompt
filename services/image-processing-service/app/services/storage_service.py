from __future__ import annotations

import uuid

from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe
from image2prompt_shared.storage import get_storage_backend

from ..config import settings
from ..dao.file_ref_dao import FileRefDao
from ..dtos.internal_dtos import CreateFileRefReq, FileRefResp, StoreImageReq


class StorageService(BaseService):
    """Stores an upload via the customer's storage backend and records a FileRef."""

    def __init__(self, *, file_ref_dao: FileRefDao) -> None:
        super().__init__()
        self.file_ref_dao = file_ref_dao

    @observe("StorageService.store")
    def store(self, req: StoreImageReq) -> FileRefResp:
        backend = get_storage_backend(req.storage_backend, base_dir=settings.local_storage_dir)
        ext = (req.filename.rsplit(".", 1)[-1] if "." in req.filename else "bin")[:10]
        key = f"{req.customer_id}/{uuid.uuid4()}.{ext}"
        stored = backend.save(req.data, key=key, content_type=req.content_type)
        return self.file_ref_dao.create(
            CreateFileRefReq(
                db=req.db,
                customer_id=req.customer_id,
                backend=stored.backend,
                location=stored.location,
                content_type=stored.content_type,
                size=stored.size,
                meta={"original_filename": req.filename},
            )
        )
