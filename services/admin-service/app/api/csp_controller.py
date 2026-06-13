from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import current_admin, get_db
from ..di import get_csp_facade
from ..dtos.internal_dtos import IngestViolationReq, ListViolationsReq
from ..facades.interfaces import ICspFacade
from ..schemas import CspDashboard, CspViolationIn, CspViolationOut

# Admin-facing dashboard (JWT-protected).
router = APIRouter(prefix="/admin/csp-violations", tags=["csp"])
# Service-to-service (trusted network) — the gateway forwards parsed reports here.
internal = APIRouter(prefix="/internal/csp-violations", tags=["csp-internal"])


@internal.post("", status_code=202)
def ingest_violation(
    payload: CspViolationIn,
    db: Session = Depends(get_db),
    facade: ICspFacade = Depends(get_csp_facade),
):
    ensure_ok(
        facade.ingest(
            IngestViolationReq(
                db=db,
                document_uri=payload.document_uri,
                violated_directive=payload.violated_directive,
                blocked_uri=payload.blocked_uri,
                source_file=payload.source_file,
                line_number=payload.line_number,
                disposition=payload.disposition,
                user_agent=payload.user_agent,
                raw=payload.raw,
            )
        )
    )
    return {"status": "accepted"}


@router.get("", response_model=CspDashboard)
def list_violations(
    limit: int = Query(default=100, le=500),
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: ICspFacade = Depends(get_csp_facade),
) -> CspDashboard:
    resp = ensure_ok(facade.list_violations(ListViolationsReq(db=db, limit=limit)))
    return CspDashboard(
        total=resp.total,
        summary=resp.summary,
        violations=[CspViolationOut.model_validate(v) for v in resp.violations],
    )
