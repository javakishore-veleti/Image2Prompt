from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from image2prompt_shared.api_errors import ensure_ok
from image2prompt_shared.auth_dep import Principal

from ..deps import admin_writer, current_admin, get_db
from ..di import get_subscriptions_facade
from ..dtos.internal_dtos import (
    AssignSubscriptionReq,
    CreatePlanReq,
    GetCustomerSubscriptionReq,
    GetPlanReq,
    ListPlanCustomersReq,
    ListPlansReq,
    UpdatePlanReq,
)
from ..facades.interfaces import ISubscriptionsFacade
from ..schemas import (
    AssignSubscription,
    CustomerSubscriptionView,
    PlanCreate,
    PlanOut,
    PlanUpdate,
    SubscriptionOut,
)
from ..tech_stacks import TECH_STACKS

# Admin-facing CRUD (JWT-protected).
router = APIRouter(prefix="/admin/subscriptions", tags=["subscriptions"])
# Service-to-service (trusted) — kb-service gates KB stacks on a customer's plan.
internal = APIRouter(prefix="/internal/subscriptions", tags=["subscriptions-internal"])


@router.get("/tech-stacks", response_model=list[str])
def list_tech_stacks(_=Depends(current_admin)):
    return TECH_STACKS


@router.get("", response_model=list[PlanOut])
def list_plans(
    search: str | None = Query(default=None),
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: ISubscriptionsFacade = Depends(get_subscriptions_facade),
):
    return ensure_ok(facade.list_plans(ListPlansReq(db=db, search=search))).plans


@router.post("", response_model=PlanOut, status_code=201)
def create_plan(
    payload: PlanCreate,
    principal: Principal = Depends(admin_writer),
    db: Session = Depends(get_db),
    facade: ISubscriptionsFacade = Depends(get_subscriptions_facade),
):
    return ensure_ok(
        facade.create_plan(
            CreatePlanReq(
                db=db, name=payload.name, description=payload.description, status=payload.status,
                stacks=[s.model_dump() for s in payload.stacks],
                actor_id=principal.id, actor_email=principal.email,
            )
        )
    ).plan


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(
    plan_id: str,
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: ISubscriptionsFacade = Depends(get_subscriptions_facade),
):
    return ensure_ok(facade.get_plan(GetPlanReq(db=db, plan_id=plan_id))).plan


@router.patch("/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: str,
    payload: PlanUpdate,
    principal: Principal = Depends(admin_writer),
    db: Session = Depends(get_db),
    facade: ISubscriptionsFacade = Depends(get_subscriptions_facade),
):
    return ensure_ok(
        facade.update_plan(
            UpdatePlanReq(
                db=db, plan_id=plan_id, name=payload.name, description=payload.description,
                status=payload.status,
                stacks=[s.model_dump() for s in payload.stacks] if payload.stacks is not None else None,
                actor_id=principal.id, actor_email=principal.email,
            )
        )
    ).plan


@router.post("/{plan_id}/customers", response_model=SubscriptionOut, status_code=201)
def assign_customer(
    plan_id: str,
    payload: AssignSubscription,
    principal: Principal = Depends(admin_writer),
    db: Session = Depends(get_db),
    facade: ISubscriptionsFacade = Depends(get_subscriptions_facade),
):
    return ensure_ok(
        facade.assign(
            AssignSubscriptionReq(
                db=db, plan_id=plan_id, customer_id=payload.customer_id,
                customer_email=payload.customer_email,
                actor_id=principal.id, actor_email=principal.email,
            )
        )
    ).subscription


@router.get("/{plan_id}/customers", response_model=list[SubscriptionOut])
def plan_customers(
    plan_id: str,
    search: str | None = Query(default=None),
    _=Depends(current_admin),
    db: Session = Depends(get_db),
    facade: ISubscriptionsFacade = Depends(get_subscriptions_facade),
):
    return ensure_ok(
        facade.list_plan_customers(ListPlanCustomersReq(db=db, plan_id=plan_id, search=search))
    ).subscriptions


@internal.get("/customer/{customer_id}", response_model=CustomerSubscriptionView)
def customer_subscription(
    customer_id: str,
    db: Session = Depends(get_db),
    facade: ISubscriptionsFacade = Depends(get_subscriptions_facade),
):
    resp = ensure_ok(facade.get_customer_subscription(GetCustomerSubscriptionReq(db=db, customer_id=customer_id)))
    if resp.subscription is None or resp.plan is None:
        return CustomerSubscriptionView(has_subscription=False)
    return CustomerSubscriptionView(
        has_subscription=True,
        plan_id=resp.plan.id,
        plan_name=resp.plan.name,
        status=resp.subscription.status,
        stacks=resp.plan.stacks or [],
    )
