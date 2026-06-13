from __future__ import annotations

import base64
import hashlib

from .base import InvokeResult, ProviderController


class MockController(ProviderController):
    """Deterministic offline provider.

    Produces a plausible reverse prompt derived from the image bytes so the full
    signup -> upload -> generate -> list flow works with zero cloud credentials.
    """

    key = "mock"
    implemented = True

    _STYLES = ["cinematic", "photorealistic", "watercolor", "isometric 3D", "film noir"]
    _LENSES = ["35mm", "50mm", "85mm portrait", "wide-angle 24mm"]
    _MOODS = ["golden-hour warmth", "moody low-key lighting", "soft diffused daylight"]

    async def invoke(
        self, *, request_id: str, instruction: str, image_base64: str, media_type: str, config: dict
    ) -> InvokeResult:
        try:
            raw_bytes = base64.b64decode(image_base64)
        except Exception:
            raw_bytes = image_base64.encode("utf-8")
        digest = hashlib.sha256(raw_bytes).digest()
        style = self._STYLES[digest[0] % len(self._STYLES)]
        lens = self._LENSES[digest[1] % len(self._LENSES)]
        mood = self._MOODS[digest[2] % len(self._MOODS)]
        text = (
            f"A {style} composition shot on a {lens} lens, featuring balanced framing and "
            f"a clear focal subject, rendered with {mood}. Rich detail, high dynamic range, "
            f"and a cohesive color palette. (mock provider — {len(raw_bytes)} bytes analyzed)"
        )
        return InvokeResult(
            output_text=text,
            raw={"provider": "mock", "bytes": len(raw_bytes), "request_id": request_id},
        )
