from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

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
    ListConnectionsReq,
    ListFilesReq,
)
from ..services.connection_provider_service import BeginConnectReq, ConnectionProviderService
from .interfaces import IConnectionsFacade


class ConnectionsFacade(BaseFacade, IConnectionsFacade):
    def __init__(
        self,
        *,
        connection_dao: ConnectionDao,
        customer_dao: CustomerDao,
        provider_service: ConnectionProviderService,
    ) -> None:
        super().__init__()
        self.connection_dao = connection_dao
        self.customer_dao = customer_dao
        self.provider_service = provider_service

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
        files = (got.connection.meta or {}).get("files", [])
        if req.search:
            needle = req.search.lower()
            files = [f for f in files if needle in f.get("name", "").lower()]
        return FileListResp(
            files=[
                FileItem(id=f["id"], name=f["name"], mime_type=f["mime_type"], size=f["size"])
                for f in files
            ]
        )
