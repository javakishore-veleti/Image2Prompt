from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class InvokeRequest(BaseModel):
    provider_key: str
    request_id: str
    instruction: str = "Generate a detailed text-to-image prompt that could recreate this image."
    image_base64: str
    media_type: str = "image/png"
    config: dict[str, Any] = {}


class InvokeResponse(BaseModel):
    provider_key: str
    request_id: str
    status: str  # "success" | "error"
    output_text: str | None = None
    raw: dict[str, Any] = {}
    latency_ms: int | None = None
    error: dict[str, Any] | None = None


class ProviderInfo(BaseModel):
    key: str
    implemented: bool
