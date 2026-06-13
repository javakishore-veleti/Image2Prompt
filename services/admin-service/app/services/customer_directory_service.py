from __future__ import annotations

import httpx

from image2prompt_shared.layers import BaseService
from image2prompt_shared.observability import observe

from ..config import settings
from ..dtos.internal_dtos import (
    CustomerActivityResp,
    CustomerConnectionsResp,
    GetCustomerActivityReq,
    GetCustomerConnectionsReq,
    ProxyCustomersReq,
    ProxyCustomersResp,
)


class CustomerDirectoryService(BaseService):
    """Reusable: fetches customers from customer-service (admin has no customer DB)."""

    @observe("CustomerDirectoryService.search")
    async def search(self, req: ProxyCustomersReq) -> ProxyCustomersResp:
        url = f"{settings.customer_service_url}/internal/customers"
        params: dict = {"limit": req.limit, "offset": req.offset}
        if req.search:
            params["search"] = req.search
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return ProxyCustomersResp(customers=resp.json())
        except httpx.HTTPError as exc:
            return ProxyCustomersResp.failure(
                error_code="upstream_error", error_message=f"customer-service unavailable: {exc}"
            )

    @observe("CustomerDirectoryService.get_connections")
    async def get_connections(self, req: GetCustomerConnectionsReq) -> CustomerConnectionsResp:
        url = f"{settings.customer_service_url}/internal/customers/{req.customer_id}/connections"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return CustomerConnectionsResp(connections=resp.json())
        except httpx.HTTPError as exc:
            return CustomerConnectionsResp.failure(
                error_code="upstream_error", error_message=f"customer-service unavailable: {exc}"
            )

    @observe("CustomerDirectoryService.get_activity")
    async def get_activity(self, req: GetCustomerActivityReq) -> CustomerActivityResp:
        url = f"{settings.customer_service_url}/internal/customers/{req.customer_id}/activity"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params={"limit": req.limit, "offset": req.offset})
                resp.raise_for_status()
                return CustomerActivityResp(entries=resp.json())
        except httpx.HTTPError as exc:
            return CustomerActivityResp.failure(
                error_code="upstream_error", error_message=f"customer-service unavailable: {exc}"
            )
