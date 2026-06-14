"""Internal req/resp dataclasses (facade -> service -> dao). DB Session in the Req."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from image2prompt_shared.dtos import BaseReq, BaseResp

from ..models import KbDocument, KbGroup, ProjectKb


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
