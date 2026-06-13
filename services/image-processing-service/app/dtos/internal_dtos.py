"""Internal req/resp dataclasses for image-processing (facade -> service -> dao)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from image2prompt_shared.dtos import BaseReq, BaseResp

from ..models import FileRef, ProcReqLog, ProcReqLogProvider


# --- top-level use case ---
@dataclass(kw_only=True)
class ProcessImageReq(BaseReq):
    db: Session
    customer_id: str
    image_bytes: bytes
    content_type: str
    filename: str
    instruction: str
    project_id: Optional[str] = None
    requested_providers: Optional[list[str]] = None


@dataclass(kw_only=True)
class ProcessFromConnectionReq(BaseReq):
    db: Session
    customer_id: str
    connection_id: str
    file_id: str
    instruction: str
    project_id: Optional[str] = None
    requested_providers: Optional[list[str]] = None


@dataclass(kw_only=True)
class ProcReqResp(BaseResp):
    request: Optional[ProcReqLog] = None


# --- storage ---
@dataclass(kw_only=True)
class StoreImageReq(BaseReq):
    db: Session
    customer_id: str
    data: bytes
    content_type: str
    filename: str
    storage_backend: str = "local"


@dataclass(kw_only=True)
class CreateFileRefReq(BaseReq):
    db: Session
    customer_id: str
    backend: str
    location: str
    content_type: str
    size: int
    meta: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class FileRefResp(BaseResp):
    file_ref: Optional[FileRef] = None


# --- provider resolution (remote: admin + customer) ---
@dataclass(kw_only=True)
class ResolveProvidersReq(BaseReq):
    customer_id: str
    requested_providers: Optional[list[str]] = None


@dataclass(kw_only=True)
class ResolveProvidersResp(BaseResp):
    selected: list[str] = field(default_factory=list)
    provider_id_map: dict = field(default_factory=dict)
    config_map: dict = field(default_factory=dict)
    storage_backend: str = "local"


# --- analytics (global, for admin) ---
@dataclass(kw_only=True)
class StatsReq(BaseReq):
    db: Session
    days: int = 14


@dataclass(kw_only=True)
class StatsResp(BaseResp):
    total_requests: int = 0
    by_status: dict = field(default_factory=dict)
    providers: list[dict] = field(default_factory=list)
    over_time: list[dict] = field(default_factory=list)


# --- available providers (remote: admin) ---
@dataclass(kw_only=True)
class ListEnabledProvidersReq(BaseReq):
    pass


@dataclass(kw_only=True)
class EnabledProvidersResp(BaseResp):
    providers: list[dict] = field(default_factory=list)


# --- ai dispatch (remote: ai-adapters) ---
@dataclass(kw_only=True)
class DispatchReq(BaseReq):
    provider_key: str
    request_id: str
    instruction: str
    image_base64: str
    media_type: str
    config: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class DispatchResp(BaseResp):
    payload: dict = field(default_factory=dict)


# --- proc-req persistence ---
@dataclass(kw_only=True)
class CreateProcReqReq(BaseReq):
    db: Session
    customer_id: str
    project_id: Optional[str]
    file_ref_id: str
    instruction: str
    selected_providers: list[str]
    provider_id_map: dict
    meta: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class ListRequestsReq(BaseReq):
    db: Session
    customer_id: str
    limit: int = 50
    offset: int = 0


@dataclass(kw_only=True)
class GetRequestReq(BaseReq):
    db: Session
    customer_id: str
    request_id: str


@dataclass(kw_only=True)
class ProcReqListResp(BaseResp):
    requests: list[ProcReqLog] = field(default_factory=list)


# --- prompts listing ---
@dataclass(kw_only=True)
class ListPromptsReq(BaseReq):
    db: Session
    customer_id: str
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(kw_only=True)
class PromptItem:
    request_id: str
    provider_result_id: str
    provider_key: str
    output_text: str
    file_ref_id: str
    created_at: object


@dataclass(kw_only=True)
class PromptListResp(BaseResp):
    items: list[PromptItem] = field(default_factory=list)


# --- provider-row result (filled after dispatch) ---
@dataclass(kw_only=True)
class ProviderRowResult:
    row: ProcReqLogProvider
