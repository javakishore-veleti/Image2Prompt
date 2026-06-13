from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.customer_dao import CustomerDao
from ..dao.preference_dao import PreferenceDao
from ..dtos.internal_dtos import CustomerResp, GetByIdReq, GetPrefsReq, PrefsResp, UpdatePrefsReq
from .interfaces import IProfileFacade


class ProfileFacade(BaseFacade, IProfileFacade):
    def __init__(self, *, customer_dao: CustomerDao, preference_dao: PreferenceDao) -> None:
        super().__init__()
        self.customer_dao = customer_dao
        self.preference_dao = preference_dao

    @observe("ProfileFacade.get_me")
    def get_me(self, req: GetByIdReq) -> CustomerResp:
        result = self.customer_dao.get_by_id(req)
        if result.customer is None:
            return CustomerResp.failure(error_code="not_found", error_message="Customer not found")
        return result

    @observe("ProfileFacade.get_preferences")
    def get_preferences(self, req: GetPrefsReq) -> PrefsResp:
        resp = self.preference_dao.get_or_create(req)
        req.db.commit()
        return resp

    @observe("ProfileFacade.update_preferences")
    def update_preferences(self, req: UpdatePrefsReq) -> PrefsResp:
        resp = self.preference_dao.update(req)
        req.db.commit()
        return resp
