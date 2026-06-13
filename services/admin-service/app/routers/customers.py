from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import settings
from ..deps import current_admin
from ..schemas import CustomerOut

# Admin views customers, but customers live in customer-service. The admin
# service proxies search/listing to customer-service's internal endpoint.
router = APIRouter(prefix="/admin/customers", tags=["admin-customers"])


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    _=Depends(current_admin),
):
    url = f"{settings.customer_service_url}/internal/customers"
    params = {"limit": limit, "offset": offset}
    if search:
        params["search"] = search
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"customer-service unavailable: {exc}")
