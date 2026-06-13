from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.customer_dao import CustomerDao
from ..dao.preference_dao import PreferenceDao
from ..dtos.internal_dtos import (
    CustomerListResp,
    CustomerResp,
    GetByIdReq,
    GetPrefsReq,
    PrefsResp,
    SearchCustomersReq,
)
from .interfaces import IInternalFacade


class InternalFacade(BaseFacade, IInternalFacade):
    """Service-to-service facade (admin-service listing/search; image-processing prefs)."""

    def __init__(self, *, customer_dao: CustomerDao, preference_dao: PreferenceDao) -> None:
        super().__init__()
        self.customer_dao = customer_dao
        self.preference_dao = preference_dao

    @observe("InternalFacade.search_customers")
    def search_customers(self, req: SearchCustomersReq) -> CustomerListResp:
        return self.customer_dao.search(req)

    @observe("InternalFacade.get_customer")
    def get_customer(self, req: GetByIdReq) -> CustomerResp:
        result = self.customer_dao.get_by_id(req)
        if result.customer is None:
            return CustomerResp.failure(error_code="not_found", error_message="Customer not found")
        return result

    @observe("InternalFacade.get_preferences")
    def get_preferences(self, req: GetPrefsReq) -> PrefsResp:
        resp = self.preference_dao.get_or_create(req)
        req.db.commit()
        return resp
