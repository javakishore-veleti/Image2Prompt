"""Real OneDrive OAuth (Microsoft Graph, authorization-code flow) + file listing.

Mirrors GoogleDriveService: graceful when unconfigured (``configured=False``),
synchronous httpx, stateless (tokens live on the connection, managed by the
facade). Microsoft Graph returns DriveItems; we keep only image files.
"""

from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

import httpx

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings

_GRAPH = "https://graph.microsoft.com/v1.0"
_ME_URL = f"{_GRAPH}/me"
_CHILDREN_URL = f"{_GRAPH}/me/drive/root/children"


def _authority() -> str:
    return f"https://login.microsoftonline.com/{settings.microsoft_oauth_tenant}/oauth2/v2.0"


@dataclass(kw_only=True)
class OneDriveAuthorizeUrlReq(BaseReq):
    state: str


@dataclass(kw_only=True)
class OneDriveAuthorizeUrlResp(BaseResp):
    configured: bool = False
    url: Optional[str] = None


@dataclass(kw_only=True)
class OneDriveExchangeReq(BaseReq):
    code: str


@dataclass(kw_only=True)
class OneDriveExchangeResp(BaseResp):
    configured: bool = False
    access_token: str = ""
    refresh_token: str = ""
    expires_at: int = 0
    email: str = ""


@dataclass(kw_only=True)
class OneDriveListReq(BaseReq):
    access_token: str
    refresh_token: str = ""
    search: Optional[str] = None


@dataclass(kw_only=True)
class OneDriveListResp(BaseResp):
    files: list[dict] = field(default_factory=list)
    access_token: str = ""
    expires_at: int = 0
    refreshed: bool = False


@dataclass(kw_only=True)
class OneDriveDownloadReq(BaseReq):
    access_token: str
    refresh_token: str = ""
    file_id: str


@dataclass(kw_only=True)
class OneDriveDownloadResp(BaseResp):
    content: bytes = b""
    content_type: str = "application/octet-stream"
    access_token: str = ""
    expires_at: int = 0
    refreshed: bool = False


class OneDriveService(BaseService):
    def is_configured(self) -> bool:
        return bool(settings.microsoft_oauth_client_id and settings.microsoft_oauth_client_secret)

    @observe("OneDriveService.authorize_url")
    def authorize_url(self, req: OneDriveAuthorizeUrlReq) -> OneDriveAuthorizeUrlResp:
        if not self.is_configured():
            return OneDriveAuthorizeUrlResp(configured=False)
        params = {
            "client_id": settings.microsoft_oauth_client_id,
            "redirect_uri": settings.microsoft_oauth_redirect_uri,
            "response_type": "code",
            "scope": settings.microsoft_oauth_scopes,
            "response_mode": "query",
            "state": req.state,
        }
        return OneDriveAuthorizeUrlResp(
            configured=True, url=f"{_authority()}/authorize?{urllib.parse.urlencode(params)}"
        )

    @observe("OneDriveService.exchange_code")
    def exchange_code(self, req: OneDriveExchangeReq) -> OneDriveExchangeResp:
        if not self.is_configured():
            return OneDriveExchangeResp(success=False, configured=False, error_code="not_configured")
        try:
            with httpx.Client(timeout=15.0) as client:
                tok = client.post(
                    f"{_authority()}/token",
                    data={
                        "code": req.code,
                        "client_id": settings.microsoft_oauth_client_id,
                        "client_secret": settings.microsoft_oauth_client_secret,
                        "redirect_uri": settings.microsoft_oauth_redirect_uri,
                        "scope": settings.microsoft_oauth_scopes,
                        "grant_type": "authorization_code",
                    },
                )
                tok.raise_for_status()
                t = tok.json()
                access = t.get("access_token", "")
                profile = client.get(_ME_URL, headers={"Authorization": f"Bearer {access}"})
                email = ""
                if profile.status_code == 200:
                    body = profile.json()
                    email = body.get("mail") or body.get("userPrincipalName") or ""
            return OneDriveExchangeResp(
                configured=True,
                access_token=access,
                refresh_token=t.get("refresh_token", ""),
                expires_at=int(time.time()) + int(t.get("expires_in", 3600)),
                email=email,
            )
        except Exception as exc:
            return OneDriveExchangeResp(success=False, configured=True, error_code="provider_error", error_message=str(exc))

    def _refresh(self, refresh_token: str) -> tuple[str, int]:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                f"{_authority()}/token",
                data={
                    "refresh_token": refresh_token,
                    "client_id": settings.microsoft_oauth_client_id,
                    "client_secret": settings.microsoft_oauth_client_secret,
                    "scope": settings.microsoft_oauth_scopes,
                    "grant_type": "refresh_token",
                },
            )
            r.raise_for_status()
            t = r.json()
            return t.get("access_token", ""), int(time.time()) + int(t.get("expires_in", 3600))

    @staticmethod
    def _to_image_files(items: list[dict]) -> list[dict]:
        out: list[dict] = []
        for it in items:
            file_facet = it.get("file") or {}
            mime = file_facet.get("mimeType", "")
            if "folder" in it or not mime.startswith("image/"):
                continue
            out.append({
                "id": it["id"],
                "name": it.get("name", ""),
                "mime_type": mime or "application/octet-stream",
                "size": int(it.get("size", 0) or 0),
            })
        return out

    @observe("OneDriveService.list_files")
    def list_files(self, req: OneDriveListReq) -> OneDriveListResp:
        if not self.is_configured():
            return OneDriveListResp(success=False, error_code="not_configured")
        access, expires_at, refreshed = req.access_token, 0, False
        try:
            if req.search:
                safe = urllib.parse.quote(req.search.replace("'", ""))
                url = f"{_GRAPH}/me/drive/root/search(q='{safe}')"
            else:
                url = _CHILDREN_URL

            def _fetch(token: str) -> httpx.Response:
                with httpx.Client(timeout=15.0) as client:
                    return client.get(
                        url,
                        params={"$top": 50, "$select": "id,name,file,folder,size"},
                        headers={"Authorization": f"Bearer {token}"},
                    )

            resp = _fetch(access)
            if resp.status_code == 401 and req.refresh_token:
                access, expires_at = self._refresh(req.refresh_token)
                refreshed = True
                resp = _fetch(access)
            resp.raise_for_status()
            files = self._to_image_files(resp.json().get("value", []))
            return OneDriveListResp(files=files, access_token=access, expires_at=expires_at, refreshed=refreshed)
        except Exception as exc:
            return OneDriveListResp(success=False, error_code="provider_error", error_message=str(exc))

    @observe("OneDriveService.download_file")
    def download_file(self, req: OneDriveDownloadReq) -> OneDriveDownloadResp:
        if not self.is_configured():
            return OneDriveDownloadResp(success=False, error_code="not_configured")
        access, expires_at, refreshed = req.access_token, 0, False
        try:
            url = f"{_GRAPH}/me/drive/items/{req.file_id}/content"

            def _fetch(token: str) -> httpx.Response:
                # Graph 302-redirects content to a pre-authed download URL.
                with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                    return client.get(url, headers={"Authorization": f"Bearer {token}"})

            resp = _fetch(access)
            if resp.status_code == 401 and req.refresh_token:
                access, expires_at = self._refresh(req.refresh_token)
                refreshed = True
                resp = _fetch(access)
            resp.raise_for_status()
            return OneDriveDownloadResp(
                content=resp.content,
                content_type=resp.headers.get("content-type", "application/octet-stream"),
                access_token=access,
                expires_at=expires_at,
                refreshed=refreshed,
            )
        except Exception as exc:
            return OneDriveDownloadResp(success=False, error_code="provider_error", error_message=str(exc))
