from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    ConnectionListResp,
    ConnectionResp,
    CreateConnectionReq,
    DisconnectReq,
    GetConnectionReq,
    ListConnectionsReq,
)
from ..models import Connection


class ConnectionDao(BaseDao):
    @observe("ConnectionDao.create")
    def create(self, req: CreateConnectionReq) -> ConnectionResp:
        conn = Connection(
            customer_id=req.customer_id,
            provider=req.provider,
            display_name=req.display_name,
            account_email=req.account_email,
            status="connected",
            meta=req.meta,
        )
        req.db.add(conn)
        req.db.flush()
        return ConnectionResp(connection=conn)

    @observe("ConnectionDao.list")
    def list(self, req: ListConnectionsReq) -> ConnectionListResp:
        rows = req.db.scalars(
            select(Connection)
            .where(Connection.customer_id == req.customer_id)
            .order_by(Connection.created_at.desc())
        ).all()
        return ConnectionListResp(connections=list(rows))

    @observe("ConnectionDao.get")
    def get(self, req: GetConnectionReq) -> ConnectionResp:
        conn = req.db.get(Connection, req.connection_id)
        if conn is None or conn.customer_id != req.customer_id:
            return ConnectionResp.failure(error_code="not_found", error_message="Connection not found")
        return ConnectionResp(connection=conn)

    @observe("ConnectionDao.delete")
    def delete(self, req: DisconnectReq) -> ConnectionResp:
        conn = req.db.get(Connection, req.connection_id)
        if conn is None or conn.customer_id != req.customer_id:
            return ConnectionResp.failure(error_code="not_found", error_message="Connection not found")
        req.db.delete(conn)
        req.db.flush()
        return ConnectionResp(connection=conn)
