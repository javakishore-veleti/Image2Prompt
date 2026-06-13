from __future__ import annotations

import base64
import hashlib

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class MockController(ProviderController):
    """Deterministic offline provider — works with zero cloud credentials."""

    key = "mock"
    implemented = True

    _STYLES = ["cinematic", "photorealistic", "watercolor", "isometric 3D", "film noir"]
    _LENSES = ["35mm", "50mm", "85mm portrait", "wide-angle 24mm"]
    _MOODS = ["golden-hour warmth", "moody low-key lighting", "soft diffused daylight"]

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        try:
            raw_bytes = base64.b64decode(req.image_base64)
        except Exception:
            raw_bytes = req.image_base64.encode("utf-8")
        digest = hashlib.sha256(raw_bytes).digest()
        style = self._STYLES[digest[0] % len(self._STYLES)]
        lens = self._LENSES[digest[1] % len(self._LENSES)]
        mood = self._MOODS[digest[2] % len(self._MOODS)]
        text = (
            f"A {style} composition shot on a {lens} lens, featuring balanced framing and "
            f"a clear focal subject, rendered with {mood}. Rich detail, high dynamic range, "
            f"and a cohesive color palette. (mock provider — {len(raw_bytes)} bytes analyzed)"
        )
        return ProviderInvokeResp(
            output_text=text,
            raw={"provider": "mock", "bytes": len(raw_bytes), "request_id": req.request_id},
        )
