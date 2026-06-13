"""Internal req/resp dataclasses for ai-adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from image2prompt_shared.dtos import BaseReq, BaseResp


# --- provider controller boundary ---
@dataclass(kw_only=True)
class ProviderInvokeReq(BaseReq):
    request_id: str
    instruction: str
    image_base64: str
    media_type: str = "image/png"
    config: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class ProviderInvokeResp(BaseResp):
    output_text: str = ""
    raw: dict = field(default_factory=dict)


# --- facade/service boundary ---
@dataclass(kw_only=True)
class InvokeReq(BaseReq):
    provider_key: str
    request_id: str
    instruction: str = "Generate a detailed text-to-image prompt that could recreate this image."
    image_base64: str
    media_type: str = "image/png"
    config: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class InvokeResp(BaseResp):
    provider_key: str = ""
    request_id: str = ""
    status: str = "success"  # business status: "success" | "error"
    output_text: Optional[str] = None
    raw: dict = field(default_factory=dict)
    latency_ms: Optional[int] = None
    error: Optional[dict] = None


@dataclass(kw_only=True)
class ListProvidersReq(BaseReq):
    pass


@dataclass(kw_only=True)
class ProviderInfoItem:
    key: str
    implemented: bool


@dataclass(kw_only=True)
class ListProvidersResp(BaseResp):
    providers: list[ProviderInfoItem] = field(default_factory=list)
