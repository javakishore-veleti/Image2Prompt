"""Internal req/resp dataclasses (facade -> service -> dao). DB Session in the Req."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from image2prompt_shared.dtos import BaseReq, BaseResp

from ..models import KbDocument, KbGroup, KbIngestJob, ProjectKb


# --- KB groups ---
@dataclass(kw_only=True)
class CreateGroupReq(BaseReq):
    db: Session
    customer_id: str
    project_id: str
    name: str


@dataclass(kw_only=True)
class ListGroupsReq(BaseReq):
    db: Session
    customer_id: str
    project_id: Optional[str] = None


@dataclass(kw_only=True)
class GroupResp(BaseResp):
    group: Optional[KbGroup] = None


@dataclass(kw_only=True)
class GroupListResp(BaseResp):
    groups: list[KbGroup] = field(default_factory=list)


# --- project KBs ---
@dataclass(kw_only=True)
class CreateKbReq(BaseReq):
    db: Session
    customer_id: str
    project_id: str
    group_id: str
    name: str
    tech_stack: str


@dataclass(kw_only=True)
class ListKbsReq(BaseReq):
    db: Session
    customer_id: str
    group_id: Optional[str] = None


@dataclass(kw_only=True)
class GetKbReq(BaseReq):
    db: Session
    customer_id: str
    kb_id: str


@dataclass(kw_only=True)
class KbResp(BaseResp):
    kb: Optional[ProjectKb] = None


@dataclass(kw_only=True)
class KbListResp(BaseResp):
    kbs: list[ProjectKb] = field(default_factory=list)


# --- documents / ingest / query ---
@dataclass(kw_only=True)
class IngestReq(BaseReq):
    db: Session
    customer_id: str
    kb_id: str
    generation_ids: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class IngestResp(BaseResp):
    ingested: int = 0
    skipped: int = 0
    doc_count: int = 0


# --- async ingestion jobs ---
@dataclass(kw_only=True)
class CreateIngestJobReq(BaseReq):
    db: Session
    customer_id: str
    kb_id: str
    generation_ids: list[str] = field(default_factory=list)


@dataclass(kw_only=True)
class GetIngestJobReq(BaseReq):
    db: Session
    customer_id: str
    kb_id: str
    job_id: str


@dataclass(kw_only=True)
class RunIngestJobReq(BaseReq):
    db: Session
    job_id: str


@dataclass(kw_only=True)
class IngestJobResp(BaseResp):
    job: Optional[KbIngestJob] = None


@dataclass(kw_only=True)
class QueryReq(BaseReq):
    db: Session
    customer_id: str
    kb_id: str
    query: str
    top_k: int = 5


@dataclass(kw_only=True)
class QueryResp(BaseResp):
    results: list[dict] = field(default_factory=list)


@dataclass(kw_only=True)
class ListDocsReq(BaseReq):
    db: Session
    customer_id: str
    kb_id: str


@dataclass(kw_only=True)
class DocListResp(BaseResp):
    docs: list[KbDocument] = field(default_factory=list)


# --- dao-internal create ---
@dataclass(kw_only=True)
class AddDocReq(BaseReq):
    db: Session
    kb_id: str
    generation_id: str
    title: Optional[str] = None
    meta: dict = field(default_factory=dict)


# --- my subscription (drives the customer's allowed tech-stack picker) ---
@dataclass(kw_only=True)
class MySubscriptionReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class MySubscriptionResp(BaseResp):
    has_subscription: bool = False
    plan_name: Optional[str] = None
    stacks: list[str] = field(default_factory=list)  # allowed stack keys
    max_kbs: Optional[int] = None
    max_docs_per_kb: Optional[int] = None
    gating_enabled: bool = True


# --- delete / lifecycle ---
@dataclass(kw_only=True)
class DeleteKbReq(BaseReq):
    db: Session
    customer_id: str
    kb_id: str


@dataclass(kw_only=True)
class DeleteGroupReq(BaseReq):
    db: Session
    customer_id: str
    group_id: str


@dataclass(kw_only=True)
class DeleteResp(BaseResp):
    deleted_kbs: int = 0
    deleted_docs: int = 0


# --- usage (billing: per-stack KB/doc counts for a customer) ---
@dataclass(kw_only=True)
class UsageReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class UsageResp(BaseResp):
    # one entry per tech stack the customer has KBs in:
    # {"stack": str, "kb_count": int, "doc_count": int}
    stacks: list[dict] = field(default_factory=list)
