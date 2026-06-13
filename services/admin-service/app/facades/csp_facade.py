from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe

from ..dao.csp_violation_dao import CspViolationDao
from ..dtos.internal_dtos import (
    CspViolationListResp,
    CspViolationResp,
    IngestViolationReq,
    ListViolationsReq,
)
from .interfaces import ICspFacade


class CspFacade(BaseFacade, ICspFacade):
    def __init__(self, *, csp_violation_dao: CspViolationDao) -> None:
        super().__init__()
        self.csp_violation_dao = csp_violation_dao

    @observe("CspFacade.ingest", metric="csp.violation.ingest")
    def ingest(self, req: IngestViolationReq) -> CspViolationResp:
        resp = self.csp_violation_dao.create(req)
        if resp.success:
            req.db.commit()
            Metrics.counter_add("csp.violation", 1, {"directive": req.violated_directive or "unknown"})
        return resp

    @observe("CspFacade.list_violations")
    def list_violations(self, req: ListViolationsReq) -> CspViolationListResp:
        return self.csp_violation_dao.list(req)
