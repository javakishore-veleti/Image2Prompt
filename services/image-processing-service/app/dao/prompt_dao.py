from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import ListPromptsReq, PromptItem, PromptListResp
from ..models import ProcReqLog, ProcReqLogProvider


class PromptDao(BaseDao):
    """Reads successful provider outputs for the Prompts page."""

    @observe("PromptDao.list")
    def list(self, req: ListPromptsReq) -> PromptListResp:
        stmt = (
            select(ProcReqLogProvider, ProcReqLog)
            .join(ProcReqLog, ProcReqLogProvider.proc_req_id == ProcReqLog.id)
            .where(
                ProcReqLog.customer_id == req.customer_id,
                ProcReqLogProvider.status == "success",
                ProcReqLogProvider.output_text.is_not(None),
            )
        )
        if req.search:
            stmt = stmt.where(ProcReqLogProvider.output_text.ilike(f"%{req.search}%"))
        stmt = stmt.order_by(ProcReqLogProvider.created_at.desc()).limit(req.limit).offset(req.offset)

        items: list[PromptItem] = []
        for provider_row, proc in req.db.execute(stmt).all():
            items.append(
                PromptItem(
                    request_id=proc.id,
                    provider_result_id=provider_row.id,
                    provider_key=provider_row.provider_key,
                    output_text=provider_row.output_text or "",
                    file_ref_id=proc.file_ref_id,
                    created_at=provider_row.created_at,
                )
            )
        return PromptListResp(items=items)
