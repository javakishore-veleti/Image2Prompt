from __future__ import annotations

from fastapi import APIRouter, Depends

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer
from ..di import get_image_facade
from ..dtos.internal_dtos import ListEnabledProvidersReq
from ..facades.interfaces import IImageFacade
from ..schemas import AvailableProvider

# Lets the customer portal show which providers it can run a request against.
router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[AvailableProvider])
async def list_providers(
    _: Principal = Depends(current_customer),
    facade: IImageFacade = Depends(get_image_facade),
):
    resp = ensure_ok(await facade.list_providers(ListEnabledProvidersReq()))
    return resp.providers
