from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok

from ..deps import admin_writer, current_admin, get_db
from ..di import get_providers_facade
from ..dtos.internal_dtos import CreateProviderReq, ListProvidersReq, UpdateProviderReq
from ..facades.interfaces import IProvidersFacade
from ..masking import mask_config
from ..models import Provider
from ..schemas import ProviderCreate, ProviderOut, ProviderUpdate

# Admin-facing CRUD (JWT-protected).
router = APIRouter(prefix="/admin/providers", tags=["providers"])
# Service-to-service (trusted network) — used by image-processing-service.
internal = APIRouter(prefix="/internal/providers", tags=["providers-internal"])


def _masked_out(provider: Provider) -> ProviderOut:
    """Admin-facing view: secret config values are masked so raw keys never
    reach the browser (the internal endpoint returns them unmasked)."""
    return ProviderOut(
        id=provider.id,
        key=provider.key,
        name=provider.name,
        category=provider.category,
        enabled=provider.enabled,
        config=mask_config(provider.config),
    )


@router.get("", response_model=list[ProviderOut])
def list_providers(
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: IProvidersFacade = Depends(get_providers_facade),
):
    resp = ensure_ok(facade.list_providers(ListProvidersReq(db=db)))
    return [_masked_out(p) for p in resp.providers]


@router.post("", response_model=ProviderOut, status_code=201)
def create_provider(
    payload: ProviderCreate,
    _=Depends(admin_writer),
    db: Session = Depends(get_db),
    facade: IProvidersFacade = Depends(get_providers_facade),
):
    resp = ensure_ok(
        facade.create_provider(
            CreateProviderReq(
                db=db,
                key=payload.key,
                name=payload.name,
                category=payload.category,
                enabled=payload.enabled,
                config=payload.config,
            )
        )
    )
    return _masked_out(resp.provider)


@router.patch("/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: str,
    payload: ProviderUpdate,
    _=Depends(admin_writer),
    db: Session = Depends(get_db),
    facade: IProvidersFacade = Depends(get_providers_facade),
):
    resp = ensure_ok(
        facade.update_provider(
            UpdateProviderReq(
                db=db,
                provider_id=provider_id,
                name=payload.name,
                category=payload.category,
                enabled=payload.enabled,
                config=payload.config,
            )
        )
    )
    return _masked_out(resp.provider)


@internal.get("", response_model=list[ProviderOut])
def internal_list_providers(
    enabled: bool | None = None,
    db: Session = Depends(get_db),
    facade: IProvidersFacade = Depends(get_providers_facade),
):
    return ensure_ok(facade.list_providers(ListProvidersReq(db=db, enabled=enabled))).providers
