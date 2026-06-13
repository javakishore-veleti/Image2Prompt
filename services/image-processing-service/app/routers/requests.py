from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..models import ProcReqLog
from ..orchestrator import process_image
from ..schemas import ProcReqOut

router = APIRouter(prefix="/requests", tags=["requests"])

DEFAULT_INSTRUCTION = (
    "Generate a detailed text-to-image prompt that could recreate this image."
)


@router.post("", response_model=ProcReqOut, status_code=201)
async def create_request(
    image: UploadFile = File(...),
    instruction: str = Form(default=DEFAULT_INSTRUCTION),
    project_id: str | None = Form(default=None),
    providers: str | None = Form(default=None),  # JSON array or comma-separated keys
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
):
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image upload")

    requested_providers = _parse_providers(providers)
    req = await process_image(
        db,
        customer_id=principal.id,
        image_bytes=data,
        content_type=image.content_type or "image/png",
        filename=image.filename or "upload.png",
        instruction=instruction,
        project_id=project_id,
        requested_providers=requested_providers,
    )
    return req


def _parse_providers(providers: str | None) -> list[str] | None:
    if not providers:
        return None
    providers = providers.strip()
    try:
        parsed = json.loads(providers)
        if isinstance(parsed, list):
            return [str(p) for p in parsed]
    except json.JSONDecodeError:
        pass
    return [p.strip() for p in providers.split(",") if p.strip()]


@router.get("", response_model=list[ProcReqOut])
def list_requests(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    rows = db.scalars(
        select(ProcReqLog)
        .where(ProcReqLog.customer_id == principal.id)
        .order_by(ProcReqLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return rows


@router.get("/{request_id}", response_model=ProcReqOut)
def get_request(
    request_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
):
    req = db.get(ProcReqLog, request_id)
    if req is None or req.customer_id != principal.id:
        raise HTTPException(status_code=404, detail="Request not found")
    return req
