from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import current_admin, get_db
from ..models import Provider
from ..schemas import ProviderCreate, ProviderOut, ProviderUpdate

# Admin-facing CRUD (JWT-protected).
router = APIRouter(prefix="/admin/providers", tags=["providers"])

# Service-to-service endpoints (trusted network, no admin JWT). Used by
# image-processing-service to resolve which providers are enabled.
internal = APIRouter(prefix="/internal/providers", tags=["providers-internal"])


@router.get("", response_model=list[ProviderOut])
def list_providers(_=Depends(current_admin), db: Session = Depends(get_db)):
    return db.scalars(select(Provider).order_by(Provider.name)).all()


@router.post("", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def create_provider(
    payload: ProviderCreate, _=Depends(current_admin), db: Session = Depends(get_db)
):
    if db.scalar(select(Provider).where(Provider.key == payload.key)):
        raise HTTPException(status_code=409, detail="Provider key already exists")
    provider = Provider(**payload.model_dump())
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.patch("/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: str,
    payload: ProviderUpdate,
    _=Depends(current_admin),
    db: Session = Depends(get_db),
):
    provider = db.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    db.commit()
    db.refresh(provider)
    return provider


@internal.get("", response_model=list[ProviderOut])
def internal_list_providers(
    enabled: bool | None = None, db: Session = Depends(get_db)
):
    stmt = select(Provider)
    if enabled is not None:
        stmt = stmt.where(Provider.enabled == enabled)
    return db.scalars(stmt.order_by(Provider.name)).all()
