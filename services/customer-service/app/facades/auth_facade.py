from __future__ import annotations

import jwt

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe, set_span_attributes
from image2prompt_shared.security import decode_token, hash_password, verify_password

from ..config import settings
from ..dao.customer_dao import CustomerDao
from ..dao.preference_dao import PreferenceDao
from ..dao.revoked_token_dao import IsRevokedReq, RevokedTokenDao, RevokeReq
from ..dtos.internal_dtos import (
    AuthResp,
    CreateCustomerReq,
    GetByEmailReq,
    GetByIdReq,
    GetPrefsReq,
    LoginReq,
    LogoutReq,
    LogoutResp,
    RefreshReq,
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
        revoked_token_dao: RevokedTokenDao,
    ) -> None:
        super().__init__()
        self.customer_dao = customer_dao
        self.preference_dao = preference_dao
        self.token_service = token_service
        self.revoked_token_dao = revoked_token_dao

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

        tok = self.token_service.issue(IssueTokenReq(customer_id=customer.id, email=customer.email))
        Metrics.counter_add("customer.signup.success")
        self.log.info("signup ok customer_id=%s", customer.id)
        return AuthResp(
            access_token=tok.access_token, refresh_token=tok.refresh_token,
            customer_id=customer.id, email=customer.email,
        )

    @observe("AuthFacade.login", metric="customer.login")
    def login(self, req: LoginReq) -> AuthResp:
        result = self.customer_dao.get_by_email(GetByEmailReq(db=req.db, email=req.email))
        customer = result.customer
        if customer is None or not verify_password(req.password, customer.password_hash):
            Metrics.counter_add("customer.login.failure")
            return AuthResp.failure(error_code="unauthorized", error_message="Invalid credentials")
        tok = self.token_service.issue(IssueTokenReq(customer_id=customer.id, email=customer.email))
        Metrics.counter_add("customer.login.success")
        return AuthResp(
            access_token=tok.access_token, refresh_token=tok.refresh_token,
            customer_id=customer.id, email=customer.email,
        )

    @observe("AuthFacade.refresh", metric="customer.refresh")
    def refresh(self, req: RefreshReq) -> AuthResp:
        try:
            claims = decode_token(
                req.refresh_token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm
            )
        except jwt.PyJWTError:
            return AuthResp.failure(error_code="unauthorized", error_message="Invalid refresh token")
        if claims.get("typ") != "refresh":
            return AuthResp.failure(error_code="unauthorized", error_message="Not a refresh token")
        jti = claims.get("jti", "")
        if self.revoked_token_dao.is_revoked(IsRevokedReq(db=req.db, jti=jti)).revoked:
            # Reuse of an already-rotated/revoked refresh token.
            return AuthResp.failure(error_code="unauthorized", error_message="Refresh token revoked")
        customer = self.customer_dao.get_by_id(
            GetByIdReq(db=req.db, customer_id=claims.get("sub", ""))
        ).customer
        if customer is None:
            return AuthResp.failure(error_code="unauthorized", error_message="Unknown customer")
        # Rotate: revoke the presented refresh token, then issue a fresh pair.
        self.revoked_token_dao.revoke(
            RevokeReq(db=req.db, jti=jti, expires_at=int(claims.get("exp", 0)), reason="rotated")
        )
        tok = self.token_service.issue(IssueTokenReq(customer_id=customer.id, email=customer.email))
        req.db.commit()
        return AuthResp(
            access_token=tok.access_token, refresh_token=tok.refresh_token,
            customer_id=customer.id, email=customer.email,
        )

    @observe("AuthFacade.logout", metric="customer.logout")
    def logout(self, req: LogoutReq) -> LogoutResp:
        try:
            claims = decode_token(
                req.refresh_token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm,
            )
        except jwt.PyJWTError:
            return LogoutResp()  # already invalid/expired — nothing to revoke
        self.revoked_token_dao.revoke(
            RevokeReq(
                db=req.db, jti=claims.get("jti", ""),
                expires_at=int(claims.get("exp", 0)), reason="logout",
            )
        )
        req.db.commit()
        return LogoutResp()
