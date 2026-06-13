from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..models import ProcReqLog, ProcReqLogProvider
from ..schemas import PromptListItem

# The "Prompts" page: a flattened, searchable list of successfully generated
# prompts (one row per provider output).
router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptListItem])
def list_prompts(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    stmt = (
        select(ProcReqLogProvider, ProcReqLog)
        .join(ProcReqLog, ProcReqLogProvider.proc_req_id == ProcReqLog.id)
        .where(
            ProcReqLog.customer_id == principal.id,
            ProcReqLogProvider.status == "success",
            ProcReqLogProvider.output_text.is_not(None),
        )
    )
    if search:
        stmt = stmt.where(ProcReqLogProvider.output_text.ilike(f"%{search}%"))
    stmt = stmt.order_by(ProcReqLogProvider.created_at.desc()).limit(limit).offset(offset)

    items: list[PromptListItem] = []
    for provider_row, req in db.execute(stmt).all():
        items.append(
            PromptListItem(
                request_id=req.id,
                provider_result_id=provider_row.id,
                provider_key=provider_row.provider_key,
                output_text=provider_row.output_text or "",
                file_ref_id=req.file_ref_id,
                created_at=provider_row.created_at,
            )
        )
    return items
