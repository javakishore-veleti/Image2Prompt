"""Service-to-service (trusted) endpoints. Consumed by customer-service billing
to meter a customer's KB usage per tech stack. No customer JWT — internal only."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import get_db
from ..di import get_kb_facade
from ..dtos.internal_dtos import UsageReq
from ..facades.interfaces import IKbFacade

router = APIRouter(prefix="/internal", tags=["kb-internal"])


@router.get("/usage/customer/{customer_id}")
def customer_usage(
    customer_id: str,
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    resp = ensure_ok(facade.usage(UsageReq(db=db, customer_id=customer_id)))
    return {"customer_id": customer_id, "stacks": resp.stacks}
