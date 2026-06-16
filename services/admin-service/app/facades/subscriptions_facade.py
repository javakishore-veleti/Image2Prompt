from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import observe

from ..dao.audit_dao import AuditDao
from ..dao.subscription_dao import SubscriptionDao
from ..dtos.internal_dtos import (
    ActiveSubscriptionListResp,
    AssignSubscriptionReq,
    CreatePlanReq,
    GetCustomerSubscriptionReq,
    GetPlanReq,
    ListActiveSubscriptionsReq,
    ListPlanCustomersReq,
    ListPlansReq,
    PlanListResp,
    PlanResp,
    RecordAuditReq,
    RevenueRollupReq,
    RevenueRollupResp,
    SubscriptionListResp,
    SubscriptionResp,
    UpdatePlanReq,
)
from ..tech_stacks import is_valid_stack
from .interfaces import ISubscriptionsFacade


def _validate_stacks(stacks) -> str | None:
    """Return an error message if the per-stack pricing list is malformed."""
    if not isinstance(stacks, list):
        return "stacks must be a list of {stack, monthly_cost}"
    for s in stacks:
        if not isinstance(s, dict) or "stack" not in s:
            return "each stack entry needs a 'stack' key"
        if not is_valid_stack(s["stack"]):
            return f"unknown tech stack: {s['stack']}"
        cost = s.get("monthly_cost", 0)
        if not isinstance(cost, (int, float)) or cost < 0:
            return f"monthly_cost for {s['stack']} must be a non-negative number"
    return None


class SubscriptionsFacade(BaseFacade, ISubscriptionsFacade):
    def __init__(self, *, subscription_dao: SubscriptionDao, audit_dao: AuditDao) -> None:
        super().__init__()
        self.subscription_dao = subscription_dao
        self.audit_dao = audit_dao

    def _audit(self, req, action, target, detail) -> None:
        self.audit_dao.record(
            RecordAuditReq(
                db=req.db, action=action, target=target, detail=detail,
                actor_id=getattr(req, "actor_id", None), actor_email=getattr(req, "actor_email", None),
            )
        )

    @observe("SubscriptionsFacade.create_plan")
    def create_plan(self, req: CreatePlanReq) -> PlanResp:
        err = _validate_stacks(req.stacks)
        if err:
            return PlanResp.failure(error_code="bad_request", error_message=err)
        resp = self.subscription_dao.create_plan(req)
        if resp.success:
            self._audit(req, "subscription.plan.create", req.name,
                        {"stacks": [s.get("stack") for s in (req.stacks or [])]})
            req.db.commit()
        return resp

    @observe("SubscriptionsFacade.update_plan")
    def update_plan(self, req: UpdatePlanReq) -> PlanResp:
        if req.stacks is not None:
            err = _validate_stacks(req.stacks)
            if err:
                return PlanResp.failure(error_code="bad_request", error_message=err)
        resp = self.subscription_dao.update_plan(req)
        if resp.success:
            self._audit(req, "subscription.plan.update", req.plan_id,
                        {"status": req.status, "stacks_changed": req.stacks is not None})
            req.db.commit()
        return resp

    @observe("SubscriptionsFacade.list_plans")
    def list_plans(self, req: ListPlansReq) -> PlanListResp:
        return self.subscription_dao.list_plans(req)

    @observe("SubscriptionsFacade.get_plan")
    def get_plan(self, req: GetPlanReq) -> PlanResp:
        return self.subscription_dao.get_plan(req)

    @observe("SubscriptionsFacade.assign")
    def assign(self, req: AssignSubscriptionReq) -> SubscriptionResp:
        resp = self.subscription_dao.assign(req)
        if resp.success:
            self._audit(req, "subscription.assign", req.customer_email or req.customer_id,
                        {"plan_id": req.plan_id})
            req.db.commit()
        return resp

    @observe("SubscriptionsFacade.list_plan_customers")
    def list_plan_customers(self, req: ListPlanCustomersReq) -> SubscriptionListResp:
        return self.subscription_dao.list_plan_customers(req)

    @observe("SubscriptionsFacade.get_customer_subscription")
    def get_customer_subscription(self, req: GetCustomerSubscriptionReq) -> SubscriptionResp:
        return self.subscription_dao.get_customer_subscription(req)

    @observe("SubscriptionsFacade.list_active_subscriptions")
    def list_active_subscriptions(
        self, req: ListActiveSubscriptionsReq
    ) -> ActiveSubscriptionListResp:
        return self.subscription_dao.list_active_subscriptions(req)

    @observe("SubscriptionsFacade.revenue_rollup")
    def revenue_rollup(self, req: RevenueRollupReq) -> RevenueRollupResp:
        return self.subscription_dao.revenue_rollup(req)
