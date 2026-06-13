from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import current_customer, get_db
from ..di import get_profile_facade
from ..dtos.internal_dtos import GetByIdReq, GetPrefsReq, ListActivityReq, UpdatePrefsReq
from ..facades.interfaces import IProfileFacade
from ..schemas import ActivityOut, CustomerOut, PreferenceOut, PreferenceUpdate

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("", response_model=CustomerOut)
def get_me(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IProfileFacade = Depends(get_profile_facade),
):
    resp = ensure_ok(facade.get_me(GetByIdReq(db=db, customer_id=principal.id)))
    return resp.customer


@router.get("/activity", response_model=list[ActivityOut])
def get_activity(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IProfileFacade = Depends(get_profile_facade),
):
    resp = ensure_ok(
        facade.list_activity(
            ListActivityReq(
                db=db, customer_id=principal.id, customer_email=principal.email,
                limit=limit, offset=offset,
            )
        )
    )
    return [ActivityOut.model_validate(e) for e in resp.entries]


@router.get("/preferences", response_model=PreferenceOut)
def get_preferences(
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IProfileFacade = Depends(get_profile_facade),
):
    resp = ensure_ok(facade.get_preferences(GetPrefsReq(db=db, customer_id=principal.id)))
    return resp.preference


@router.put("/preferences", response_model=PreferenceOut)
def update_preferences(
    payload: PreferenceUpdate,
    principal: Principal = Depends(current_customer),
    db: Session = Depends(get_db),
    facade: IProfileFacade = Depends(get_profile_facade),
):
    resp = ensure_ok(
        facade.update_preferences(
            UpdatePrefsReq(
                db=db,
                customer_id=principal.id,
                default_provider_keys=payload.default_provider_keys,
                storage_backend=payload.storage_backend,
                prefs=payload.prefs,
            )
        )
    )
    return resp.preference
