from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe

from ..config import settings
from ..dao.kb_dao import KbDao
from ..dtos.internal_dtos import (
    AddDocReq,
    CreateGroupReq,
    CreateIngestJobReq,
    CreateKbReq,
    DeleteGroupReq,
    DeleteKbReq,
    DeleteResp,
    DocListResp,
    GetIngestJobReq,
    GetKbReq,
    GroupListResp,
    GroupResp,
    IngestJobResp,
    IngestReq,
    IngestResp,
    KbListResp,
    KbResp,
    ListDocsReq,
    ListGroupsReq,
    ListKbsReq,
    MySubscriptionReq,
    MySubscriptionResp,
    QueryReq,
    QueryResp,
    RunIngestJobReq,
    UsageReq,
    UsageResp,
)
from ..services.clients import GenerationClient, SubscriptionClient
from ..services.embedder import Embedder
from ..services.vectorstores import build_vector_store
from ..tech_stacks import TECH_STACKS, is_valid_stack
from .interfaces import IKbFacade


def _doc_text(gen: dict) -> tuple[str, str]:
    """Build (embedding_text, title) from a resolved generation. Embeds the
    instruction + the generated prompt + light metadata (chosen ingest shape)."""
    prompts = gen.get("prompts") or []
    prompt = prompts[0]["output_text"] if prompts else ""
    providers = ",".join(p.get("provider_key", "") for p in prompts)
    parts = [gen.get("instruction") or "", prompt]
    if providers:
        parts.append(f"providers: {providers}")
    title = (prompt or gen.get("instruction") or "")[:200]
    return "\n\n".join(p for p in parts if p), title


class KbFacade(BaseFacade, IKbFacade):
    def __init__(
        self,
        *,
        kb_dao: KbDao,
        embedder: Embedder,
        subscription_client: SubscriptionClient,
        generation_client: GenerationClient,
    ) -> None:
        super().__init__()
        self.kb_dao = kb_dao
        self.embedder = embedder
        self.subscription_client = subscription_client
        self.generation_client = generation_client

    # --- groups ---
    @observe("KbFacade.create_group")
    def create_group(self, req: CreateGroupReq) -> GroupResp:
        resp = self.kb_dao.create_group(req)
        if resp.success:
            req.db.commit()
        return resp

    @observe("KbFacade.list_groups")
    def list_groups(self, req: ListGroupsReq) -> GroupListResp:
        return self.kb_dao.list_groups(req)

    # --- kbs ---
    @observe("KbFacade.create_kb", metric="kb.create")
    async def create_kb(self, req: CreateKbReq) -> KbResp:
        if not is_valid_stack(req.tech_stack):
            return KbResp.failure(error_code="bad_request", error_message=f"unknown tech stack: {req.tech_stack}")
        # Subscription gating: the customer's plan must include this stack, and the
        # plan's KB quota (if any) must not be exceeded.
        if settings.kb_require_subscription:
            sub = await self.subscription_client.get_customer_subscription(req.customer_id)
            allowed = {s.get("stack") for s in (sub.get("stacks") or [])}
            if not sub.get("has_subscription") or req.tech_stack not in allowed:
                return KbResp.failure(
                    error_code="forbidden",
                    error_message=f"Your subscription does not include the '{req.tech_stack}' tech stack.",
                )
            max_kbs = sub.get("max_kbs")
            if max_kbs is not None and self.kb_dao.count_kbs(req.db, req.customer_id) >= max_kbs:
                return KbResp.failure(
                    error_code="forbidden",
                    error_message=f"Your plan's limit of {max_kbs} knowledge bases has been reached.",
                )
        store = build_vector_store(req.tech_stack)
        resp = self.kb_dao.create_kb(req, backend_ready=store.ready())
        if resp.success:
            req.db.commit()
            Metrics.counter_add("kb.create", 1, {"stack": req.tech_stack})
        return resp

    @observe("KbFacade.list_kbs")
    def list_kbs(self, req: ListKbsReq) -> KbListResp:
        return self.kb_dao.list_kbs(req)

    @observe("KbFacade.get_kb")
    def get_kb(self, req: GetKbReq) -> KbResp:
        return self.kb_dao.get_kb(req)

    @observe("KbFacade.list_docs")
    def list_docs(self, req: ListDocsReq) -> DocListResp:
        got = self.kb_dao.get_kb(GetKbReq(db=req.db, customer_id=req.customer_id, kb_id=req.kb_id))
        if not got.success:
            return DocListResp.failure(error_code=got.error_code, error_message=got.error_message)
        return self.kb_dao.list_docs(req)

    # --- ingest / query ---
    @observe("KbFacade.ingest", metric="kb.ingest")
    async def ingest(self, req: IngestReq) -> IngestResp:
        got = self.kb_dao.get_kb(GetKbReq(db=req.db, customer_id=req.customer_id, kb_id=req.kb_id))
        if not got.success:
            return IngestResp.failure(error_code=got.error_code, error_message=got.error_message)
        kb = got.kb
        # Plan quota: cap docs per KB (None = unlimited). Over-cap docs are skipped.
        remaining = None
        if settings.kb_require_subscription:
            sub = await self.subscription_client.get_customer_subscription(req.customer_id)
            cap = sub.get("max_docs_per_kb")
            if cap is not None:
                remaining = max(0, cap - (kb.doc_count or 0))
        gens = await self.generation_client.resolve(req.customer_id, req.generation_ids)
        store = build_vector_store(kb.tech_stack)
        ingested = skipped = 0
        for gen in gens:
            gid = gen.get("id")
            if not gid or self.kb_dao.doc_exists(req.db, kb.id, gid):
                skipped += 1
                continue
            if remaining is not None and ingested >= remaining:
                skipped += 1  # plan's per-KB document quota reached
                continue
            text, title = _doc_text(gen)
            if not text:
                skipped += 1
                continue
            vector = self.embedder.embed(text)
            payload = {
                "generation_id": gid, "title": title, "project_id": gen.get("project_id"),
                "file_ref_id": gen.get("file_ref_id"),
            }
            store.upsert(namespace=kb.id, doc_id=gid, vector=vector, text=text, payload=payload, db=req.db)
            self.kb_dao.add_doc(AddDocReq(db=req.db, kb_id=kb.id, generation_id=gid, title=title, meta=payload))
            ingested += 1
        kb.doc_count = (kb.doc_count or 0) + ingested
        req.db.commit()
        Metrics.counter_add("kb.ingest", ingested, {"stack": kb.tech_stack})
        return IngestResp(ingested=ingested, skipped=skipped, doc_count=kb.doc_count)

    # --- async ingestion (large batches run in the background; clients poll) ---
    @observe("KbFacade.create_ingest_job")
    def create_ingest_job(self, req: CreateIngestJobReq) -> IngestJobResp:
        got = self.kb_dao.get_kb(GetKbReq(db=req.db, customer_id=req.customer_id, kb_id=req.kb_id))
        if not got.success:
            return IngestJobResp.failure(error_code=got.error_code, error_message=got.error_message)
        resp = self.kb_dao.create_ingest_job(req)
        req.db.commit()
        return resp

    @observe("KbFacade.get_ingest_job")
    def get_ingest_job(self, req: GetIngestJobReq) -> IngestJobResp:
        return self.kb_dao.get_ingest_job(req)

    @observe("KbFacade.run_ingest_job")
    async def run_ingest_job(self, req: RunIngestJobReq) -> IngestJobResp:
        """Background worker: run the (already-validated) job's ingest and record
        progress on the job. Self-contained + fail-safe — errors land on the job."""
        job = self.kb_dao.get_ingest_job_by_id(req.db, req.job_id)
        if job is None:
            return IngestJobResp.failure(error_code="not_found", error_message="Ingest job not found")
        job.status = "running"
        req.db.commit()
        try:
            resp = await self.ingest(
                IngestReq(db=req.db, customer_id=job.customer_id, kb_id=job.kb_id,
                          generation_ids=list(job.requested_ids or []))
            )
            if not resp.success:
                job.status, job.error = "error", resp.error_message
            else:
                job.status, job.ingested, job.skipped = "done", resp.ingested, resp.skipped
        except Exception as exc:  # never let a background failure escape
            job.status, job.error = "error", str(exc)[:1024]
        req.db.commit()
        return IngestJobResp(job=job)

    @observe("KbFacade.query", metric="kb.query")
    async def query(self, req: QueryReq) -> QueryResp:
        got = self.kb_dao.get_kb(GetKbReq(db=req.db, customer_id=req.customer_id, kb_id=req.kb_id))
        if not got.success:
            return QueryResp.failure(error_code=got.error_code, error_message=got.error_message)
        kb = got.kb
        store = build_vector_store(kb.tech_stack)
        vector = self.embedder.embed(req.query)
        hits = store.query(namespace=kb.id, vector=vector, text=req.query, top_k=req.top_k, db=req.db)
        results = [
            {
                "generation_id": h.get("payload", {}).get("generation_id", h.get("id")),
                "score": round(float(h.get("score", 0.0)), 4),
                "title": h.get("payload", {}).get("title"),
                "project_id": h.get("payload", {}).get("project_id"),
            }
            for h in hits
        ]
        return QueryResp(results=results)

    # --- usage (consumed by customer-service billing over /internal) ---
    @observe("KbFacade.usage")
    def usage(self, req: UsageReq) -> UsageResp:
        return self.kb_dao.usage_by_customer(req)

    @observe("KbFacade.my_subscription")
    async def my_subscription(self, req: MySubscriptionReq) -> MySubscriptionResp:
        """The customer's allowed stacks + quotas, used to scope the portal's KB
        picker. When gating is off (or no subscription), fall back to the full
        catalog so KB creation still works in dev."""
        gating = settings.kb_require_subscription
        if not gating:
            return MySubscriptionResp(has_subscription=False, stacks=list(TECH_STACKS), gating_enabled=False)
        sub = await self.subscription_client.get_customer_subscription(req.customer_id)
        if not sub.get("has_subscription"):
            return MySubscriptionResp(has_subscription=False, stacks=[], gating_enabled=True)
        stacks = [s.get("stack") for s in (sub.get("stacks") or []) if s.get("stack")]
        return MySubscriptionResp(
            has_subscription=True, plan_name=sub.get("plan_name"), stacks=stacks,
            max_kbs=sub.get("max_kbs"), max_docs_per_kb=sub.get("max_docs_per_kb"),
            gating_enabled=True,
        )

    # --- delete / lifecycle ---
    def _purge_kb(self, db, kb) -> int:
        """Remove a KB's vectors from its backend, then its doc + KB rows. Returns
        docs removed. Vector cleanup is best-effort (never blocks the DB delete)."""
        store = build_vector_store(kb.tech_stack)
        store.delete_namespace(namespace=kb.id, db=db)
        return self.kb_dao.delete_kb_row(db, kb)

    @observe("KbFacade.delete_kb", metric="kb.delete")
    def delete_kb(self, req: DeleteKbReq) -> DeleteResp:
        got = self.kb_dao.get_kb(GetKbReq(db=req.db, customer_id=req.customer_id, kb_id=req.kb_id))
        if not got.success:
            return DeleteResp.failure(error_code=got.error_code, error_message=got.error_message)
        docs = self._purge_kb(req.db, got.kb)
        req.db.commit()
        Metrics.counter_add("kb.delete", 1, {"stack": got.kb.tech_stack})
        return DeleteResp(deleted_kbs=1, deleted_docs=docs)

    @observe("KbFacade.delete_group", metric="kb.group.delete")
    def delete_group(self, req: DeleteGroupReq) -> DeleteResp:
        group = self.kb_dao.get_group(req.db, req.customer_id, req.group_id)
        if group is None:
            return DeleteResp.failure(error_code="not_found", error_message="Group not found")
        kbs = self.kb_dao.list_kbs(
            ListKbsReq(db=req.db, customer_id=req.customer_id, group_id=req.group_id)
        ).kbs
        docs = sum(self._purge_kb(req.db, kb) for kb in kbs)
        self.kb_dao.delete_group_row(req.db, group)
        req.db.commit()
        return DeleteResp(deleted_kbs=len(kbs), deleted_docs=docs)
