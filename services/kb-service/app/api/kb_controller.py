from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..db import db as _db
from ..deps import current_customer, get_db
from ..di import get_kb_facade
from ..dtos.internal_dtos import (
    CreateGroupReq,
    CreateIngestJobReq,
    CreateKbReq,
    DeleteGroupReq,
    DeleteKbReq,
    GetIngestJobReq,
    GetKbReq,
    IngestReq,
    ListDocsReq,
    ListGroupsReq,
    ListKbsReq,
    MySubscriptionReq,
    QueryReq,
    RunIngestJobReq,
)
from ..facades.interfaces import IKbFacade
from ..schemas import (
    DocOut,
    GroupCreate,
    GroupOut,
    IngestJobOut,
    IngestOut,
    IngestRequest,
    KbCreate,
    KbOut,
    QueryOut,
    QueryRequest,
)
from ..tech_stacks import TECH_STACKS


async def _run_ingest_job(job_id: str) -> None:
    """Background worker — own DB session, delegates to the facade (fail-safe)."""
    with _db.SessionLocal() as session:
        await get_kb_facade().run_ingest_job(RunIngestJobReq(db=session, job_id=job_id))

router = APIRouter(tags=["kb"])


@router.get("/tech-stacks", response_model=list[str])
def tech_stacks(_: Principal = Depends(current_customer)):
    return TECH_STACKS


@router.get("/my-subscription")
async def my_subscription(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    """The current customer's allowed tech stacks + quotas — scopes the KB picker."""
    resp = ensure_ok(await facade.my_subscription(MySubscriptionReq(db=db, customer_id=principal.id)))
    return {
        "has_subscription": resp.has_subscription,
        "plan_name": resp.plan_name,
        "stacks": resp.stacks,
        "max_kbs": resp.max_kbs,
        "max_docs_per_kb": resp.max_docs_per_kb,
        "gating_enabled": resp.gating_enabled,
    }


# --- groups ---
@router.post("/groups", response_model=GroupOut, status_code=201)
def create_group(
    payload: GroupCreate,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    return ensure_ok(
        facade.create_group(
            CreateGroupReq(db=db, customer_id=principal.id, project_id=payload.project_id, name=payload.name)
        )
    ).group


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    resp = ensure_ok(
        facade.delete_group(DeleteGroupReq(db=db, customer_id=principal.id, group_id=group_id))
    )
    return {"deleted_kbs": resp.deleted_kbs, "deleted_docs": resp.deleted_docs}


@router.get("/groups", response_model=list[GroupOut])
def list_groups(
    project_id: str | None = Query(default=None),
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    return ensure_ok(
        facade.list_groups(ListGroupsReq(db=db, customer_id=principal.id, project_id=project_id))
    ).groups


# --- kbs ---
@router.post("/kbs", response_model=KbOut, status_code=201)
async def create_kb(
    payload: KbCreate,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    return ensure_ok(
        await facade.create_kb(
            CreateKbReq(
                db=db, customer_id=principal.id, project_id=payload.project_id,
                group_id=payload.group_id, name=payload.name, tech_stack=payload.tech_stack,
            )
        )
    ).kb


@router.get("/kbs", response_model=list[KbOut])
def list_kbs(
    group_id: str | None = Query(default=None),
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    return ensure_ok(facade.list_kbs(ListKbsReq(db=db, customer_id=principal.id, group_id=group_id))).kbs


@router.get("/kbs/{kb_id}", response_model=KbOut)
def get_kb(
    kb_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    return ensure_ok(facade.get_kb(GetKbReq(db=db, customer_id=principal.id, kb_id=kb_id))).kb


@router.delete("/kbs/{kb_id}")
def delete_kb(
    kb_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    resp = ensure_ok(facade.delete_kb(DeleteKbReq(db=db, customer_id=principal.id, kb_id=kb_id)))
    return {"deleted_kbs": resp.deleted_kbs, "deleted_docs": resp.deleted_docs}


@router.get("/kbs/{kb_id}/documents", response_model=list[DocOut])
def list_docs(
    kb_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    return ensure_ok(facade.list_docs(ListDocsReq(db=db, customer_id=principal.id, kb_id=kb_id))).docs


@router.post("/kbs/{kb_id}/ingest", response_model=IngestOut)
async def ingest(
    kb_id: str,
    payload: IngestRequest,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    resp = ensure_ok(
        await facade.ingest(
            IngestReq(db=db, customer_id=principal.id, kb_id=kb_id, generation_ids=payload.generation_ids)
        )
    )
    return IngestOut(ingested=resp.ingested, skipped=resp.skipped, doc_count=resp.doc_count)


@router.post("/kbs/{kb_id}/ingest-async", response_model=IngestJobOut, status_code=202)
def ingest_async(
    kb_id: str,
    payload: IngestRequest,
    background: BackgroundTasks,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    """Queue a background ingest and return a job to poll. Large batches don't block."""
    job = ensure_ok(
        facade.create_ingest_job(
            CreateIngestJobReq(
                db=db, customer_id=principal.id, kb_id=kb_id, generation_ids=payload.generation_ids
            )
        )
    ).job
    background.add_task(_run_ingest_job, job.id)
    return job


@router.get("/kbs/{kb_id}/ingest-jobs/{job_id}", response_model=IngestJobOut)
def ingest_job(
    kb_id: str,
    job_id: str,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    return ensure_ok(
        facade.get_ingest_job(
            GetIngestJobReq(db=db, customer_id=principal.id, kb_id=kb_id, job_id=job_id)
        )
    ).job


@router.post("/kbs/{kb_id}/query", response_model=QueryOut)
async def query(
    kb_id: str,
    payload: QueryRequest,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IKbFacade = Depends(get_kb_facade),
):
    resp = ensure_ok(
        await facade.query(
            QueryReq(db=db, customer_id=principal.id, kb_id=kb_id, query=payload.query, top_k=payload.top_k)
        )
    )
    return QueryOut(results=resp.results)
