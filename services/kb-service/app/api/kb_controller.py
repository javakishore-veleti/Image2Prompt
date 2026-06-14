from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..di import get_kb_facade
from ..dtos.internal_dtos import (
    CreateGroupReq,
    CreateKbReq,
    GetKbReq,
    IngestReq,
    ListDocsReq,
    ListGroupsReq,
    ListKbsReq,
    QueryReq,
)
from ..facades.interfaces import IKbFacade
from ..schemas import (
    DocOut,
    GroupCreate,
    GroupOut,
    IngestOut,
    IngestRequest,
    KbCreate,
    KbOut,
    QueryOut,
    QueryRequest,
)
from ..tech_stacks import TECH_STACKS

router = APIRouter(tags=["kb"])


@router.get("/tech-stacks", response_model=list[str])
def tech_stacks(_: Principal = Depends(current_customer)):
    return TECH_STACKS


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
