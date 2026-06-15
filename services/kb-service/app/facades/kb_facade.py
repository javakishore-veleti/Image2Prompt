from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe

from ..config import settings
from ..dao.kb_dao import KbDao
from ..dtos.internal_dtos import (
    AddDocReq,
    CreateGroupReq,
    CreateKbReq,
    DocListResp,
    GetKbReq,
    GroupListResp,
    GroupResp,
    IngestReq,
    IngestResp,
    KbListResp,
    KbResp,
    ListDocsReq,
    ListGroupsReq,
    ListKbsReq,
    QueryReq,
    QueryResp,
    UsageReq,
    UsageResp,
)
from ..services.clients import GenerationClient, SubscriptionClient
from ..services.embedder import Embedder
from ..services.vectorstores import build_vector_store
from ..tech_stacks import is_valid_stack
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
        # Subscription gating: the customer's plan must include this stack.
        if settings.kb_require_subscription:
            sub = await self.subscription_client.get_customer_subscription(req.customer_id)
            allowed = {s.get("stack") for s in (sub.get("stacks") or [])}
            if not sub.get("has_subscription") or req.tech_stack not in allowed:
                return KbResp.failure(
                    error_code="forbidden",
                    error_message=f"Your subscription does not include the '{req.tech_stack}' tech stack.",
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
        gens = await self.generation_client.resolve(req.customer_id, req.generation_ids)
        store = build_vector_store(kb.tech_stack)
        ingested = skipped = 0
        for gen in gens:
            gid = gen.get("id")
            if not gid or self.kb_dao.doc_exists(req.db, kb.id, gid):
                skipped += 1
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
