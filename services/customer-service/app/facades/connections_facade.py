from __future__ import annotations

import jwt

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe
from image2prompt_shared.security import create_access_token, decode_token

from ..config import settings
from ..dao.connection_dao import ConnectionDao
from ..dao.customer_dao import CustomerDao
from ..dtos.internal_dtos import (
    ConnectionListResp,
    ConnectionResp,
    ConnectReq,
    CreateConnectionReq,
    DisconnectReq,
    FileItem,
    FileListResp,
    GetByIdReq,
    GetConnectionReq,
    GoogleAuthorizeReq,
    GoogleAuthorizeResp,
    GoogleCallbackReq,
    ListConnectionsReq,
    ListFilesReq,
)
from ..services.connection_provider_service import BeginConnectReq, ConnectionProviderService
from ..services.google_drive_service import (
    AuthorizeUrlReq,
    DriveListReq,
    ExchangeReq,
    GoogleDriveService,
)
from .interfaces import IConnectionsFacade


class ConnectionsFacade(BaseFacade, IConnectionsFacade):
    def __init__(
        self,
        *,
        connection_dao: ConnectionDao,
        customer_dao: CustomerDao,
        provider_service: ConnectionProviderService,
        google_drive_service: GoogleDriveService,
    ) -> None:
        super().__init__()
        self.connection_dao = connection_dao
        self.customer_dao = customer_dao
        self.provider_service = provider_service
        self.google_drive = google_drive_service

    @observe("ConnectionsFacade.connect", metric="connection.connect")
    def connect(self, req: ConnectReq) -> ConnectionResp:
        customer = self.customer_dao.get_by_id(GetByIdReq(db=req.db, customer_id=req.customer_id)).customer
        email = customer.email if customer else ""
        begun = self.provider_service.begin_connect(
            BeginConnectReq(provider=req.provider, customer_email=email)
        )
        if not begun.success:
            return ConnectionResp.failure(error_code=begun.error_code, error_message=begun.error_message)
        resp = self.connection_dao.create(
            CreateConnectionReq(
                db=req.db,
                customer_id=req.customer_id,
                provider=req.provider,
                display_name=begun.display_name,
                account_email=begun.account_email,
                meta=begun.meta or {},
            )
        )
        req.db.commit()
        return resp

    # ---------------- Real Google Drive OAuth ----------------
    @observe("ConnectionsFacade.google_authorize")
    def google_authorize(self, req: GoogleAuthorizeReq) -> GoogleAuthorizeResp:
        # Signed, short-lived state carrying the customer id (no server-side store).
        state = create_access_token(
            subject=req.customer_id,
            token_type="oauth_state",
            email="",
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expire_minutes=10,
        )
        url = self.google_drive.authorize_url(AuthorizeUrlReq(state=state))
        if not url.configured:
            return GoogleAuthorizeResp.failure(
                error_code="not_configured", error_message="Google OAuth is not configured"
            )
        return GoogleAuthorizeResp(configured=True, authorize_url=url.url)

    @observe("ConnectionsFacade.google_callback")
    def google_callback(self, req: GoogleCallbackReq) -> ConnectionResp:
        try:
            claims = decode_token(req.state, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
        except jwt.PyJWTError:
            return ConnectionResp.failure(error_code="unauthorized", error_message="Invalid OAuth state")
        if claims.get("typ") != "oauth_state":
            return ConnectionResp.failure(error_code="unauthorized", error_message="Bad OAuth state")
        customer_id = claims.get("sub", "")
        ex = self.google_drive.exchange_code(ExchangeReq(code=req.code))
        if not ex.success:
            return ConnectionResp.failure(error_code=ex.error_code or "provider_error", error_message=ex.error_message)
        resp = self.connection_dao.create(
            CreateConnectionReq(
                db=req.db,
                customer_id=customer_id,
                provider="google_drive",
                display_name="Google Drive",
                account_email=ex.email,
                meta={
                    "real": True,
                    "access_token": ex.access_token,
                    "refresh_token": ex.refresh_token,
                    "expires_at": ex.expires_at,
                },
            )
        )
        req.db.commit()
        return resp

    @observe("ConnectionsFacade.list_connections")
    def list_connections(self, req: ListConnectionsReq) -> ConnectionListResp:
        return self.connection_dao.list(req)

    @observe("ConnectionsFacade.disconnect")
    def disconnect(self, req: DisconnectReq) -> ConnectionResp:
        resp = self.connection_dao.delete(req)
        if resp.success:
            req.db.commit()
        return resp

    @observe("ConnectionsFacade.list_files")
    def list_files(self, req: ListFilesReq) -> FileListResp:
        got = self.connection_dao.get(
            GetConnectionReq(db=req.db, customer_id=req.customer_id, connection_id=req.connection_id)
        )
        if not got.success:
            return FileListResp.failure(error_code=got.error_code, error_message=got.error_message)
        conn = got.connection
        meta = conn.meta or {}

        # Live Google Drive listing for real connections.
        if conn.provider == "google_drive" and meta.get("real"):
            drive = self.google_drive.list_files(
                DriveListReq(
                    access_token=meta.get("access_token", ""),
                    refresh_token=meta.get("refresh_token", ""),
                    search=req.search,
                )
            )
            if not drive.success:
                return FileListResp.failure(error_code=drive.error_code, error_message=drive.error_message)
            if drive.refreshed and drive.access_token:  # persist refreshed token
                meta["access_token"] = drive.access_token
                meta["expires_at"] = drive.expires_at
                conn.meta = dict(meta)
                req.db.commit()
            return FileListResp(
                files=[FileItem(id=f["id"], name=f["name"], mime_type=f["mime_type"], size=f["size"]) for f in drive.files]
            )

        # Mock providers: stored sample files.
        files = meta.get("files", [])
        if req.search:
            needle = req.search.lower()
            files = [f for f in files if needle in f.get("name", "").lower()]
        return FileListResp(
            files=[FileItem(id=f["id"], name=f["name"], mime_type=f["mime_type"], size=f["size"]) for f in files]
        )
