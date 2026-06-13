from __future__ import annotations

from sqlalchemy import case, func, select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import StatsReq, StatsResp
from ..models import ProcReqLog, ProcReqLogProvider


class StatsDao(BaseDao):
    """Global aggregates across all customers, for the admin dashboard."""

    @observe("StatsDao.stats")
    def stats(self, req: StatsReq) -> StatsResp:
        db = req.db
        total = db.scalar(select(func.count(ProcReqLog.id))) or 0

        by_status = {
            status: count
            for status, count in db.execute(
                select(ProcReqLog.status, func.count(ProcReqLog.id)).group_by(ProcReqLog.status)
            ).all()
        }

        success_case = case((ProcReqLogProvider.status == "success", 1), else_=0)
        providers = []
        for key, count, success, avg_latency in db.execute(
            select(
                ProcReqLogProvider.provider_key,
                func.count(ProcReqLogProvider.id),
                func.sum(success_case),
                func.avg(ProcReqLogProvider.latency_ms),
            ).group_by(ProcReqLogProvider.provider_key)
        ).all():
            success = int(success or 0)
            providers.append(
                {
                    "provider_key": key,
                    "count": int(count),
                    "success": success,
                    "error": int(count) - success,
                    "avg_latency_ms": round(float(avg_latency), 1) if avg_latency is not None else None,
                }
            )

        over_time = [
            {"date": str(day), "count": int(count)}
            for day, count in db.execute(
                select(func.date(ProcReqLog.created_at), func.count(ProcReqLog.id))
                .group_by(func.date(ProcReqLog.created_at))
                .order_by(func.date(ProcReqLog.created_at).desc())
                .limit(req.days)
            ).all()
        ]
        over_time.reverse()

        return StatsResp(
            total_requests=int(total),
            by_status=by_status,
            providers=providers,
            over_time=over_time,
        )
