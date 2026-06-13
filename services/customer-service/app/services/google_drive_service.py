"""Real Google Drive OAuth (authorization-code flow) + Drive file listing.

Graceful: if the OAuth client isn't configured, ``configured=False`` is returned
and callers fall back / show a message. All HTTP is synchronous httpx. Tokens are
stored on the connection by the facade; this service is stateless.
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

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


@dataclass(kw_only=True)
class AuthorizeUrlReq(BaseReq):
    state: str


@dataclass(kw_only=True)
class AuthorizeUrlResp(BaseResp):
    configured: bool = False
    url: Optional[str] = None


@dataclass(kw_only=True)
class ExchangeReq(BaseReq):
    code: str


@dataclass(kw_only=True)
class ExchangeResp(BaseResp):
    configured: bool = False
    access_token: str = ""
    refresh_token: str = ""
    expires_at: int = 0
    email: str = ""


@dataclass(kw_only=True)
class DriveListReq(BaseReq):
    access_token: str
    refresh_token: str = ""
    search: Optional[str] = None


@dataclass(kw_only=True)
class DriveListResp(BaseResp):
    files: list[dict] = field(default_factory=list)
    access_token: str = ""  # possibly refreshed; facade persists it
    expires_at: int = 0
    refreshed: bool = False


class GoogleDriveService(BaseService):
    def is_configured(self) -> bool:
        return bool(settings.google_oauth_client_id and settings.google_oauth_client_secret)

    @observe("GoogleDriveService.authorize_url")
    def authorize_url(self, req: AuthorizeUrlReq) -> AuthorizeUrlResp:
        if not self.is_configured():
            return AuthorizeUrlResp(configured=False)
        params = {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": settings.google_oauth_scopes,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": req.state,
        }
        return AuthorizeUrlResp(configured=True, url=f"{_AUTH_URL}?{urllib.parse.urlencode(params)}")

    @observe("GoogleDriveService.exchange_code")
    def exchange_code(self, req: ExchangeReq) -> ExchangeResp:
        if not self.is_configured():
            return ExchangeResp(success=False, configured=False, error_code="not_configured")
        try:
            with httpx.Client(timeout=15.0) as client:
                tok = client.post(
                    _TOKEN_URL,
                    data={
                        "code": req.code,
                        "client_id": settings.google_oauth_client_id,
                        "client_secret": settings.google_oauth_client_secret,
                        "redirect_uri": settings.google_oauth_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                tok.raise_for_status()
                t = tok.json()
                access = t.get("access_token", "")
                profile = client.get(
                    _USERINFO_URL, headers={"Authorization": f"Bearer {access}"}
                )
                email = profile.json().get("email", "") if profile.status_code == 200 else ""
            return ExchangeResp(
                configured=True,
                access_token=access,
                refresh_token=t.get("refresh_token", ""),
                expires_at=int(time.time()) + int(t.get("expires_in", 3600)),
                email=email,
            )
        except Exception as exc:
            return ExchangeResp(success=False, configured=True, error_code="provider_error", error_message=str(exc))

    def _refresh(self, refresh_token: str) -> tuple[str, int]:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                _TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": settings.google_oauth_client_id,
                    "client_secret": settings.google_oauth_client_secret,
                    "grant_type": "refresh_token",
                },
            )
            r.raise_for_status()
            t = r.json()
            return t.get("access_token", ""), int(time.time()) + int(t.get("expires_in", 3600))

    @observe("GoogleDriveService.list_files")
    def list_files(self, req: DriveListReq) -> DriveListResp:
        if not self.is_configured():
            return DriveListResp(success=False, error_code="not_configured")
        access, expires_at, refreshed = req.access_token, 0, False
        try:
            q = "mimeType contains 'image/' and trashed = false"
            if req.search:
                safe = req.search.replace("'", "")
                q += f" and name contains '{safe}'"

            def _fetch(token: str) -> httpx.Response:
                with httpx.Client(timeout=15.0) as client:
                    return client.get(
                        _DRIVE_FILES_URL,
                        params={"q": q, "fields": "files(id,name,mimeType,size)", "pageSize": 25},
                        headers={"Authorization": f"Bearer {token}"},
                    )

            resp = _fetch(access)
            if resp.status_code == 401 and req.refresh_token:
                access, expires_at = self._refresh(req.refresh_token)
                refreshed = True
                resp = _fetch(access)
            resp.raise_for_status()
            files = [
                {
                    "id": f["id"], "name": f["name"],
                    "mime_type": f.get("mimeType", "application/octet-stream"),
                    "size": int(f.get("size", 0) or 0),
                }
                for f in resp.json().get("files", [])
            ]
            return DriveListResp(files=files, access_token=access, expires_at=expires_at, refreshed=refreshed)
        except Exception as exc:
            return DriveListResp(success=False, error_code="provider_error", error_message=str(exc))
