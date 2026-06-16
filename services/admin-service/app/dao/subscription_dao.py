from __future__ import annotations

from sqlalchemy import func, or_, select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

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
    RevenueRollupReq,
    RevenueRollupResp,
    SubscriptionListResp,
    SubscriptionResp,
    UpdatePlanReq,
)
from ..models import CustomerSubscription, SubscriptionPlan


class SubscriptionDao(BaseDao):
    # --- plans ---
    @observe("SubscriptionDao.create_plan")
    def create_plan(self, req: CreatePlanReq) -> PlanResp:
        if req.db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.name == req.name)):
            return PlanResp.failure(error_code="conflict", error_message="Plan name already exists")
        plan = SubscriptionPlan(
            name=req.name, description=req.description, status=req.status, stacks=req.stacks or [],
            max_kbs=req.max_kbs, max_docs_per_kb=req.max_docs_per_kb,
        )
        req.db.add(plan)
        req.db.flush()
        return PlanResp(plan=plan)

    @observe("SubscriptionDao.update_plan")
    def update_plan(self, req: UpdatePlanReq) -> PlanResp:
        plan = req.db.get(SubscriptionPlan, req.plan_id)
        if plan is None:
            return PlanResp.failure(error_code="not_found", error_message="Plan not found")
        if req.name is not None:
            plan.name = req.name
        if req.description is not None:
            plan.description = req.description
        if req.status is not None:
            plan.status = req.status
        if req.stacks is not None:
            plan.stacks = req.stacks
        if req.set_max_kbs:
            plan.max_kbs = req.max_kbs
        if req.set_max_docs_per_kb:
            plan.max_docs_per_kb = req.max_docs_per_kb
        req.db.flush()
        return PlanResp(plan=plan)

    @observe("SubscriptionDao.list_plans")
    def list_plans(self, req: ListPlansReq) -> PlanListResp:
        stmt = select(SubscriptionPlan)
        if req.search:
            like = f"%{req.search}%"
            stmt = stmt.where(SubscriptionPlan.name.ilike(like))
        stmt = stmt.order_by(SubscriptionPlan.name)
        return PlanListResp(plans=list(req.db.scalars(stmt).all()))

    @observe("SubscriptionDao.get_plan")
    def get_plan(self, req: GetPlanReq) -> PlanResp:
        plan = req.db.get(SubscriptionPlan, req.plan_id)
        if plan is None:
            return PlanResp.failure(error_code="not_found", error_message="Plan not found")
        return PlanResp(plan=plan)

    # --- customer assignments ---
    @observe("SubscriptionDao.assign")
    def assign(self, req: AssignSubscriptionReq) -> SubscriptionResp:
        plan = req.db.get(SubscriptionPlan, req.plan_id)
        if plan is None:
            return SubscriptionResp.failure(error_code="not_found", error_message="Plan not found")
        existing = req.db.scalar(
            select(CustomerSubscription).where(CustomerSubscription.customer_id == req.customer_id)
        )
        if existing is None:
            existing = CustomerSubscription(customer_id=req.customer_id)
            req.db.add(existing)
        existing.plan_id = req.plan_id
        existing.customer_email = req.customer_email
        existing.status = "active"
        req.db.flush()
        return SubscriptionResp(subscription=existing, plan=plan)

    @observe("SubscriptionDao.list_plan_customers")
    def list_plan_customers(self, req: ListPlanCustomersReq) -> SubscriptionListResp:
        stmt = select(CustomerSubscription).where(CustomerSubscription.plan_id == req.plan_id)
        if req.search:
            like = f"%{req.search}%"
            stmt = stmt.where(
                or_(
                    CustomerSubscription.customer_email.ilike(like),
                    CustomerSubscription.customer_id.ilike(like),
                )
            )
        stmt = stmt.order_by(CustomerSubscription.created_at.desc())
        return SubscriptionListResp(subscriptions=list(req.db.scalars(stmt).all()))

    @observe("SubscriptionDao.revenue_rollup")
    def revenue_rollup(self, req: RevenueRollupReq) -> RevenueRollupResp:
        """Contracted MRR per plan = (active subscribers) × (plan list price), where
        plan list price = sum of the plan's per-stack monthly costs. This is
        contracted/list revenue, not usage-adjusted billed revenue."""
        counts = dict(
            req.db.execute(
                select(CustomerSubscription.plan_id, func.count(CustomerSubscription.id))
                .where(CustomerSubscription.status == "active")
                .group_by(CustomerSubscription.plan_id)
            ).all()
        )
        rows = []
        total = 0.0
        for plan in req.db.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.name)).all():
            price = float(sum((s.get("monthly_cost") or 0) for s in (plan.stacks or [])))
            customers = int(counts.get(plan.id, 0))
            mrr = round(price * customers, 2)
            total += mrr
            rows.append(
                {"plan_id": plan.id, "plan_name": plan.name, "customers": customers,
                 "plan_price": round(price, 2), "mrr": mrr}
            )
        return RevenueRollupResp(total_mrr=round(total, 2), plans=rows)

    @observe("SubscriptionDao.list_active_subscriptions")
    def list_active_subscriptions(self, req: ListActiveSubscriptionsReq) -> ActiveSubscriptionListResp:
        """All active subscriptions joined with their plan — consumed by the
        scheduled monthly-billing sweep in customer-service."""
        rows = req.db.execute(
            select(CustomerSubscription, SubscriptionPlan)
            .join(SubscriptionPlan, SubscriptionPlan.id == CustomerSubscription.plan_id)
            .where(CustomerSubscription.status == "active")
            .order_by(CustomerSubscription.created_at)
        ).all()
        return ActiveSubscriptionListResp(
            items=[
                {
                    "customer_id": sub.customer_id,
                    "customer_email": sub.customer_email,
                    "plan_id": plan.id,
                    "plan_name": plan.name,
                    "status": sub.status,
                    "stacks": plan.stacks or [],
                }
                for sub, plan in rows
            ]
        )

    @observe("SubscriptionDao.get_customer_subscription")
    def get_customer_subscription(self, req: GetCustomerSubscriptionReq) -> SubscriptionResp:
        sub = req.db.scalar(
            select(CustomerSubscription).where(CustomerSubscription.customer_id == req.customer_id)
        )
        if sub is None:
            return SubscriptionResp()  # no subscription is a valid "none" state
        plan = req.db.get(SubscriptionPlan, sub.plan_id)
        return SubscriptionResp(subscription=sub, plan=plan)
