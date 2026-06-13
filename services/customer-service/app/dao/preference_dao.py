from __future__ import annotations

from sqlalchemy import select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import GetPrefsReq, PrefsResp, UpdatePrefsReq
from ..models import CustomerPreference


class PreferenceDao(BaseDao):
    @observe("PreferenceDao.get_or_create")
    def get_or_create(self, req: GetPrefsReq) -> PrefsResp:
        prefs = req.db.scalar(
            select(CustomerPreference).where(CustomerPreference.customer_id == req.customer_id)
        )
        if prefs is None:
            prefs = CustomerPreference(customer_id=req.customer_id, storage_backend="local")
            req.db.add(prefs)
            req.db.flush()
        return PrefsResp(preference=prefs)

    @observe("PreferenceDao.update")
    def update(self, req: UpdatePrefsReq) -> PrefsResp:
        prefs = req.db.scalar(
            select(CustomerPreference).where(CustomerPreference.customer_id == req.customer_id)
        )
        if prefs is None:
            prefs = CustomerPreference(customer_id=req.customer_id, storage_backend="local")
            req.db.add(prefs)
            req.db.flush()
        if req.default_provider_keys is not None:
            prefs.default_provider_keys = req.default_provider_keys
        if req.storage_backend is not None:
            prefs.storage_backend = req.storage_backend
        if req.prefs is not None:
            prefs.prefs = req.prefs
        req.db.flush()
        return PrefsResp(preference=prefs)
