from __future__ import annotations

from sqlalchemy import func, select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    AddDocReq,
    CreateGroupReq,
    CreateKbReq,
    DocListResp,
    GetKbReq,
    GroupListResp,
    GroupResp,
    KbListResp,
    KbResp,
    ListDocsReq,
    ListGroupsReq,
    ListKbsReq,
)
from ..models import KbDocument, KbGroup, ProjectKb


class KbDao(BaseDao):
    # --- groups ---
    @observe("KbDao.create_group")
    def create_group(self, req: CreateGroupReq) -> GroupResp:
        g = KbGroup(customer_id=req.customer_id, project_id=req.project_id, name=req.name)
        req.db.add(g)
        req.db.flush()
        return GroupResp(group=g)

    @observe("KbDao.list_groups")
    def list_groups(self, req: ListGroupsReq) -> GroupListResp:
        stmt = select(KbGroup).where(KbGroup.customer_id == req.customer_id)
        if req.project_id:
            stmt = stmt.where(KbGroup.project_id == req.project_id)
        return GroupListResp(groups=list(req.db.scalars(stmt.order_by(KbGroup.created_at.desc())).all()))

    # --- kbs ---
    @observe("KbDao.create_kb")
    def create_kb(self, req: CreateKbReq, *, backend_ready: bool) -> KbResp:
        kb = ProjectKb(
            group_id=req.group_id, customer_id=req.customer_id, project_id=req.project_id,
            name=req.name, tech_stack=req.tech_stack, backend_ready=backend_ready,
        )
        req.db.add(kb)
        req.db.flush()
        return KbResp(kb=kb)

    @observe("KbDao.list_kbs")
    def list_kbs(self, req: ListKbsReq) -> KbListResp:
        stmt = select(ProjectKb).where(ProjectKb.customer_id == req.customer_id)
        if req.group_id:
            stmt = stmt.where(ProjectKb.group_id == req.group_id)
        return KbListResp(kbs=list(req.db.scalars(stmt.order_by(ProjectKb.created_at.desc())).all()))

    @observe("KbDao.get_kb")
    def get_kb(self, req: GetKbReq) -> KbResp:
        kb = req.db.get(ProjectKb, req.kb_id)
        if kb is None or kb.customer_id != req.customer_id:
            return KbResp.failure(error_code="not_found", error_message="KB not found")
        return KbResp(kb=kb)

    # --- documents ---
    @observe("KbDao.get_doc")
    def doc_exists(self, db, kb_id: str, generation_id: str) -> bool:
        return db.scalar(
            select(func.count(KbDocument.id)).where(
                KbDocument.kb_id == kb_id, KbDocument.generation_id == generation_id
            )
        ) > 0

    @observe("KbDao.add_doc")
    def add_doc(self, req: AddDocReq) -> None:
        req.db.add(
            KbDocument(kb_id=req.kb_id, generation_id=req.generation_id, title=req.title, meta=req.meta)
        )
        req.db.flush()

    @observe("KbDao.list_docs")
    def list_docs(self, req: ListDocsReq) -> DocListResp:
        rows = req.db.scalars(
            select(KbDocument).where(KbDocument.kb_id == req.kb_id).order_by(KbDocument.created_at.desc())
        ).all()
        return DocListResp(docs=list(rows))

    def get_doc_by_generation(self, db, kb_id: str, generation_id: str):
        return db.scalar(
            select(KbDocument).where(
                KbDocument.kb_id == kb_id, KbDocument.generation_id == generation_id
            )
        )
