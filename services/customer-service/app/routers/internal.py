from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Customer, CustomerPreference
from ..schemas import CustomerOut, PreferenceOut

# Service-to-service endpoints (trusted network). Consumed by admin-service
# (customer listing/search) and image-processing-service (preferences).
router = APIRouter(prefix="/internal/customers", tags=["customers-internal"])


@router.get("", response_model=list[CustomerOut])
def list_customers(
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Customer)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Customer.email.ilike(like), Customer.name.ilike(like)))
    stmt = stmt.order_by(Customer.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/{customer_id}/preferences", response_model=PreferenceOut)
def get_preferences(customer_id: str, db: Session = Depends(get_db)):
    prefs = db.scalar(
        select(CustomerPreference).where(CustomerPreference.customer_id == customer_id)
    )
    if prefs is None:
        # Sensible default if a customer somehow has no prefs row.
        return PreferenceOut(customer_id=customer_id, default_provider_keys=[], storage_backend="local")
    return prefs
