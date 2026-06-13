from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AvailableProvider(BaseModel):
    key: str
    name: str


class ProviderResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_key: str
    provider_id: str | None = None
    status: str
    output_text: str | None = None
    latency_ms: int | None = None
    error: dict[str, Any] | None = None
    created_at: datetime


class ProcReqOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    project_id: str | None = None
    file_ref_id: str
    instruction: str
    status: str
    requested_providers: list[str] = []
    meta: dict[str, Any] = {}
    created_at: datetime
    providers: list[ProviderResultOut] = []


class PromptListItem(BaseModel):
    """A generated prompt (one successful provider output) for the Prompts page."""

    request_id: str
    provider_result_id: str
    provider_key: str
    output_text: str
    file_ref_id: str
    created_at: datetime
