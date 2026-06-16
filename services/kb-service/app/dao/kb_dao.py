from __future__ import annotations

from sqlalchemy import delete, func, select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    AddDocReq,
    CreateGroupReq,
    CreateIngestJobReq,
    CreateKbReq,
    DocListResp,
    GetIngestJobReq,
    GetKbReq,
    GroupListResp,
    GroupResp,
    IngestJobResp,
    KbListResp,
    KbResp,
    ListDocsReq,
    ListGroupsReq,
    ListKbsReq,
    UsageReq,
    UsageResp,
)
from ..models import KbDocument, KbGroup, KbIngestJob, ProjectKb


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

    def get_group(self, db, customer_id: str, group_id: str) -> KbGroup | None:
        g = db.get(KbGroup, group_id)
        return g if (g is not None and g.customer_id == customer_id) else None

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

    def count_kbs(self, db, customer_id: str) -> int:
        return int(db.scalar(
            select(func.count(ProjectKb.id)).where(ProjectKb.customer_id == customer_id)
        ) or 0)

    @observe("KbDao.get_kb")
    def get_kb(self, req: GetKbReq) -> KbResp:
        kb = req.db.get(ProjectKb, req.kb_id)
        if kb is None or kb.customer_id != req.customer_id:
            return KbResp.failure(error_code="not_found", error_message="KB not found")
        return KbResp(kb=kb)

    @observe("KbDao.delete_kb_row")
    def delete_kb_row(self, db, kb: ProjectKb) -> int:
        """Delete a KB's document rows and the KB itself. Returns docs removed.
        (Vector data is removed separately via the vector store's delete_namespace.)"""
        doc_count = db.scalar(
            select(func.count(KbDocument.id)).where(KbDocument.kb_id == kb.id)
        ) or 0
        db.execute(delete(KbDocument).where(KbDocument.kb_id == kb.id))
        db.delete(kb)
        db.flush()
        return int(doc_count)

    @observe("KbDao.delete_group_row")
    def delete_group_row(self, db, group: KbGroup) -> None:
        db.delete(group)
        db.flush()

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

    # --- async ingestion jobs ---
    @observe("KbDao.create_ingest_job")
    def create_ingest_job(self, req: CreateIngestJobReq) -> IngestJobResp:
        job = KbIngestJob(
            kb_id=req.kb_id, customer_id=req.customer_id, status="pending",
            requested_ids=list(req.generation_ids or []), requested=len(req.generation_ids or []),
        )
        req.db.add(job)
        req.db.flush()
        return IngestJobResp(job=job)

    @observe("KbDao.get_ingest_job")
    def get_ingest_job(self, req: GetIngestJobReq) -> IngestJobResp:
        job = req.db.get(KbIngestJob, req.job_id)
        if job is None or job.customer_id != req.customer_id or job.kb_id != req.kb_id:
            return IngestJobResp.failure(error_code="not_found", error_message="Ingest job not found")
        return IngestJobResp(job=job)

    def get_ingest_job_by_id(self, db, job_id: str) -> KbIngestJob | None:
        return db.get(KbIngestJob, job_id)

    # --- usage (billing) ---
    @observe("KbDao.usage_by_customer")
    def usage_by_customer(self, req: UsageReq) -> UsageResp:
        """Per-stack KB count + summed doc_count for a customer (the billable shape)."""
        rows = req.db.execute(
            select(
                ProjectKb.tech_stack,
                func.count(ProjectKb.id),
                func.coalesce(func.sum(ProjectKb.doc_count), 0),
            )
            .where(ProjectKb.customer_id == req.customer_id)
            .group_by(ProjectKb.tech_stack)
            .order_by(ProjectKb.tech_stack)
        ).all()
        return UsageResp(
            stacks=[
                {"stack": stack, "kb_count": int(kb_count), "doc_count": int(doc_count)}
                for stack, kb_count, doc_count in rows
            ]
        )
