"""Mock cloud-drive OAuth + file listing.

Stands in for real OAuth: ``begin_connect`` fabricates a connected account and a
sample image listing per provider. Swap this service's internals for real OAuth
(authorize URL, token exchange, provider file APIs) without touching the facade
or controllers.
"""

from __future__ import annotations

from dataclasses import dataclass

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

PROVIDERS = {
    "google_drive": "Google Drive",
    "onedrive": "OneDrive",
    "dropbox": "Dropbox",
}

_SAMPLE_FILES = {
    "google_drive": ["sunset-beach.jpg", "team-offsite.png", "product-shot.jpg"],
    "onedrive": ["scan-receipt.png", "whiteboard.jpg"],
    "dropbox": ["mockup-v2.png", "logo-draft.png", "hero-banner.jpg"],
}


@dataclass(kw_only=True)
class BeginConnectReq(BaseReq):
    provider: str
    customer_email: str


@dataclass(kw_only=True)
class BeginConnectResp(BaseResp):
    display_name: str = ""
    account_email: str = ""
    meta: dict = None  # type: ignore[assignment]


class ConnectionProviderService(BaseService):
    @observe("ConnectionProviderService.begin_connect")
    def begin_connect(self, req: BeginConnectReq) -> BeginConnectResp:
        if req.provider not in PROVIDERS:
            return BeginConnectResp.failure(
                error_code="bad_request", error_message=f"Unknown provider: {req.provider}"
            )
        files = [
            {"id": f"{req.provider}-{i}", "name": name, "mime_type": _mime(name), "size": 1000 * (i + 1)}
            for i, name in enumerate(_SAMPLE_FILES.get(req.provider, []))
        ]
        # Mock account derived from the customer's email (real OAuth returns this).
        account = req.customer_email or f"user@{req.provider}.example"
        return BeginConnectResp(
            display_name=PROVIDERS[req.provider],
            account_email=account,
            meta={"mock": True, "files": files},
        )


def _mime(name: str) -> str:
    return "image/png" if name.lower().endswith(".png") else "image/jpeg"
