from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    CreateProcReqReq,
    GetRequestReq,
    ListRequestsReq,
    ProcReqListResp,
    ProcReqResp,
)
from ..models import ProcReqLog, ProcReqLogProvider


class ProcReqDao(BaseDao):
    @observe("ProcReqDao.create")
    def create(self, req: CreateProcReqReq) -> ProcReqResp:
        proc = ProcReqLog(
            customer_id=req.customer_id,
            project_id=req.project_id,
            file_ref_id=req.file_ref_id,
            instruction=req.instruction,
            status="processing",
            requested_providers=req.selected_providers,
            meta=req.meta,
        )
        req.db.add(proc)
        req.db.flush()
        for key in req.selected_providers:
            req.db.add(
                ProcReqLogProvider(
                    proc_req_id=proc.id,
                    provider_key=key,
                    provider_id=req.provider_id_map.get(key),
                    status="pending",
                    request_payload={"instruction": req.instruction, "provider_key": key},
                )
            )
        req.db.flush()
        return ProcReqResp(request=proc)

    @observe("ProcReqDao.list")
    def list(self, req: ListRequestsReq) -> ProcReqListResp:
        rows = req.db.scalars(
            select(ProcReqLog)
            .where(ProcReqLog.customer_id == req.customer_id)
            .order_by(ProcReqLog.created_at.desc())
            .limit(req.limit)
            .offset(req.offset)
        ).all()
        return ProcReqListResp(requests=list(rows))

    @observe("ProcReqDao.get")
    def get(self, req: GetRequestReq) -> ProcReqResp:
        proc = req.db.get(ProcReqLog, req.request_id)
        if proc is None or proc.customer_id != req.customer_id:
            return ProcReqResp.failure(error_code="not_found", error_message="Request not found")
        return ProcReqResp(request=proc)
