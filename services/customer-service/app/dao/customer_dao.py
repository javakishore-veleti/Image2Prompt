from __future__ import annotations

from sqlalchemy import func, or_, select

from image2prompt_shared.layers import BaseDao
from image2prompt_shared.observability import observe

from ..dtos.internal_dtos import (
    CountCustomersReq,
    CountResp,
    CreateCustomerReq,
    CustomerListResp,
    CustomerResp,
    GetByEmailReq,
    GetByIdReq,
    SearchCustomersReq,
)
from ..models import Customer


class CustomerDao(BaseDao):
    """DB access for customers. Singleton; session arrives inside each Req."""

    @observe("CustomerDao.get_by_email")
    def get_by_email(self, req: GetByEmailReq) -> CustomerResp:
        customer = req.db.scalar(select(Customer).where(Customer.email == req.email))
        return CustomerResp(customer=customer)

    @observe("CustomerDao.get_by_id")
    def get_by_id(self, req: GetByIdReq) -> CustomerResp:
        return CustomerResp(customer=req.db.get(Customer, req.customer_id))

    @observe("CustomerDao.create")
    def create(self, req: CreateCustomerReq) -> CustomerResp:
        customer = Customer(email=req.email, password_hash=req.password_hash, name=req.name)
        req.db.add(customer)
        req.db.flush()
        return CustomerResp(customer=customer)

    @observe("CustomerDao.search")
    def search(self, req: SearchCustomersReq) -> CustomerListResp:
        stmt = select(Customer)
        if req.search:
            like = f"%{req.search}%"
            stmt = stmt.where(or_(Customer.email.ilike(like), Customer.name.ilike(like)))
        stmt = stmt.order_by(Customer.created_at.desc()).limit(req.limit).offset(req.offset)
        return CustomerListResp(customers=list(req.db.scalars(stmt).all()))

    @observe("CustomerDao.count")
    def count(self, req: CountCustomersReq) -> CountResp:
        return CountResp(count=int(req.db.scalar(select(func.count(Customer.id))) or 0))
