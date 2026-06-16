"""HTTP request/response models at the API boundary."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class GroupCreate(BaseModel):
    project_id: str
    name: str


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str
    created_at: Any


class KbCreate(BaseModel):
    group_id: str
    project_id: str
    name: str
    tech_stack: str


class KbOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    group_id: str
    project_id: str
    name: str
    tech_stack: str
    status: str
    doc_count: int
    backend_ready: bool


class DocOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    generation_id: str
    title: str | None = None
    created_at: Any


class IngestRequest(BaseModel):
    generation_ids: list[str] = []


class IngestOut(BaseModel):
    ingested: int
    skipped: int
    doc_count: int


class IngestJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kb_id: str
    status: str
    requested: int
    ingested: int
    skipped: int
    error: str | None = None


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class QueryResultOut(BaseModel):
    generation_id: str
    score: float
    title: str | None = None
    project_id: str | None = None


class QueryOut(BaseModel):
    results: list[QueryResultOut] = []
