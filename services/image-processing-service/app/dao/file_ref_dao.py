from __future__ import annotations

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import CreateFileRefReq, FileRefResp
from ..models import FileRef


class FileRefDao(BaseDao):
    @observe("FileRefDao.create")
    def create(self, req: CreateFileRefReq) -> FileRefResp:
        file_ref = FileRef(
            customer_id=req.customer_id,
            backend=req.backend,
            location=req.location,
            content_type=req.content_type,
            size=req.size,
            meta=req.meta,
        )
        req.db.add(file_ref)
        req.db.flush()
        return FileRefResp(file_ref=file_ref)
