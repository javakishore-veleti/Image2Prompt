from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..di import get_image_facade
from ..dtos.internal_dtos import ListPromptsReq
from ..facades.interfaces import IImageFacade
from ..schemas import PromptListItem

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptListItem])
def list_prompts(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IImageFacade = Depends(get_image_facade),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    resp = ensure_ok(
        facade.list_prompts(
            ListPromptsReq(
                db=db, customer_id=principal.id, search=search, limit=limit, offset=offset
            )
        )
    )
    return [
        PromptListItem(
            request_id=i.request_id,
            provider_result_id=i.provider_result_id,
            provider_key=i.provider_key,
            output_text=i.output_text,
            file_ref_id=i.file_ref_id,
            created_at=i.created_at,
        )
        for i in resp.items
    ]
