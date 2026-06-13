"""Fetches a connected file's bytes from customer-service (which holds the
provider tokens). Used by the generate-from-connection flow."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from image2prompt_shared.dtos import BaseReq, BaseResp
from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings


@dataclass(kw_only=True)
class FetchFileReq(BaseReq):
    customer_id: str
    connection_id: str
    file_id: str


@dataclass(kw_only=True)
class FetchFileResp(BaseResp):
    content: bytes = b""
    content_type: str = "application/octet-stream"


class ConnectionFetchService(BaseService):
    @observe("ConnectionFetchService.fetch")
    async def fetch(self, req: FetchFileReq) -> FetchFileResp:
        url = (
            f"{settings.customer_service_url}/internal/customers/{req.customer_id}"
            f"/connections/{req.connection_id}/files/{req.file_id}/content"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return FetchFileResp(
                    content=resp.content,
                    content_type=resp.headers.get("content-type", "application/octet-stream"),
                )
        except httpx.HTTPError as exc:
            return FetchFileResp(success=False, error_code="upstream_error", error_message=str(exc))
