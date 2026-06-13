"""Request/response objects for the router client (keyword-only dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(kw_only=True)
class BaseResp:
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass(kw_only=True)
class RouteReq:
    router: str               # "openrouter" | "litellm"
    instruction: str
    image_base64: str
    media_type: str = "image/png"
    model: Optional[str] = None   # override the router's default model
    max_tokens: int = 400


@dataclass(kw_only=True)
class RouteResp(BaseResp):
    router: str = ""
    model: str = ""
    output_text: str = ""
    raw: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class RouterInfo:
    name: str
    enabled: bool
