from __future__ import annotations

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe, set_span_attributes
from image2prompt_shared.security import hash_password, verify_password

from ..dao.customer_dao import CustomerDao
from ..dao.preference_dao import PreferenceDao
from ..dtos.internal_dtos import (
    AuthResp,
    CreateCustomerReq,
    GetByEmailReq,
    GetPrefsReq,
    LoginReq,
    SignupReq,
)
from ..services.token_service import IssueTokenReq, TokenService
from .interfaces import IAuthFacade


class AuthFacade(BaseFacade, IAuthFacade):
    """Use-case orchestration for signup/login. Flow: facade -> service/dao."""

    def __init__(
        self,
        *,
        customer_dao: CustomerDao,
        preference_dao: PreferenceDao,
        token_service: TokenService,
    ) -> None:
        super().__init__()
        self.customer_dao = customer_dao
        self.preference_dao = preference_dao
        self.token_service = token_service

    @observe("AuthFacade.signup", metric="customer.signup")
    def signup(self, req: SignupReq) -> AuthResp:
        set_span_attributes({"customer.email": req.email})
        existing = self.customer_dao.get_by_email(GetByEmailReq(db=req.db, email=req.email))
        if existing.customer is not None:
            self.log.info("signup rejected: email already registered")
            return AuthResp.failure(error_code="conflict", error_message="Email already registered")

        created = self.customer_dao.create(
            CreateCustomerReq(
                db=req.db, email=req.email, password_hash=hash_password(req.password), name=req.name
            )
        )
        customer = created.customer
        # default preferences (empty provider list => use admin defaults)
        self.preference_dao.get_or_create(GetPrefsReq(db=req.db, customer_id=customer.id))
        req.db.commit()

        token = self.token_service.issue(
            IssueTokenReq(customer_id=customer.id, email=customer.email)
        ).access_token
        Metrics.counter_add("customer.signup.success")
        self.log.info("signup ok customer_id=%s", customer.id)
        return AuthResp(access_token=token, customer_id=customer.id, email=customer.email)

    @observe("AuthFacade.login", metric="customer.login")
    def login(self, req: LoginReq) -> AuthResp:
        result = self.customer_dao.get_by_email(GetByEmailReq(db=req.db, email=req.email))
        customer = result.customer
        if customer is None or not verify_password(req.password, customer.password_hash):
            Metrics.counter_add("customer.login.failure")
            return AuthResp.failure(error_code="unauthorized", error_message="Invalid credentials")
        token = self.token_service.issue(
            IssueTokenReq(customer_id=customer.id, email=customer.email)
        ).access_token
        Metrics.counter_add("customer.login.success")
        return AuthResp(access_token=token, customer_id=customer.id, email=customer.email)
