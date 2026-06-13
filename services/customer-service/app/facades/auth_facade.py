from __future__ import annotations

import jwt

from image2prompt_shared.layers import BaseFacade
from image2prompt_shared.observability import Metrics, observe, set_span_attributes
from image2prompt_shared.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

from ..config import settings
from ..dao.audit_dao import AuditDao
from ..dao.customer_dao import CustomerDao
from ..dao.preference_dao import PreferenceDao
from ..dao.revoked_token_dao import (
    IsFamilyRevokedReq,
    IsRevokedReq,
    RevokedTokenDao,
    RevokeFamilyReq,
    RevokeReq,
)
from ..dtos.internal_dtos import (
    AuthResp,
    CreateCustomerReq,
    GetByEmailReq,
    GetByIdReq,
    GetPrefsReq,
    LoginReq,
    LogoutReq,
    LogoutResp,
    MessageResp,
    RecordAuditReq,
    RefreshReq,
    RequestPasswordResetReq,
    ResetPasswordReq,
    SendVerificationReq,
    SignupReq,
    VerifyEmailReq,
)
from ..services.email_service import EmailService, SendEmailReq
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
        email_service: EmailService,
        audit_dao: AuditDao,
    ) -> None:
        super().__init__()
        self.customer_dao = customer_dao
        self.preference_dao = preference_dao
        self.token_service = token_service
        self.revoked_token_dao = revoked_token_dao
        self.email_service = email_service
        self.audit_dao = audit_dao

    def _audit(self, db, action, *, actor_id=None, actor_email=None, target=None, detail=None) -> None:
        self.audit_dao.record(
            RecordAuditReq(
                db=db, action=action, actor_id=actor_id, actor_email=actor_email,
                target=target, detail=detail or {},
            )
        )

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
        self._audit(req.db, "customer.signup", actor_id=customer.id, actor_email=customer.email)
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
            self._audit(
                req.db, "customer.login.failure",
                actor_id=customer.id if customer else None, actor_email=req.email,
            )
            req.db.commit()
            return AuthResp.failure(error_code="unauthorized", error_message="Invalid credentials")
        tok = self.token_service.issue(IssueTokenReq(customer_id=customer.id, email=customer.email))
        Metrics.counter_add("customer.login.success")
        self._audit(req.db, "customer.login.success", actor_id=customer.id, actor_email=customer.email)
        req.db.commit()
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
        family_id = claims.get("fid", "")
        exp = int(claims.get("exp", 0))
        # If the whole family was already revoked (logout, or a prior reuse), reject.
        if family_id and self.revoked_token_dao.is_family_revoked(
            IsFamilyRevokedReq(db=req.db, family_id=family_id)
        ).revoked:
            return AuthResp.failure(error_code="unauthorized", error_message="Refresh token revoked")
        if self.revoked_token_dao.is_revoked(IsRevokedReq(db=req.db, jti=jti)).revoked:
            # Reuse of an already-rotated refresh token => likely theft. Burn the
            # entire family so any live descendant token is invalidated too.
            if family_id:
                self.revoked_token_dao.revoke_family(
                    RevokeFamilyReq(db=req.db, family_id=family_id, expires_at=exp, reason="reuse")
                )
                self._audit(
                    req.db, "customer.token_reuse_detected",
                    actor_id=claims.get("sub"), actor_email=claims.get("email"),
                )
                req.db.commit()
                self.log.warning("refresh-token reuse detected; revoked family=%s", family_id)
            Metrics.counter_add("customer.refresh.reuse")
            return AuthResp.failure(error_code="unauthorized", error_message="Refresh token revoked")
        customer = self.customer_dao.get_by_id(
            GetByIdReq(db=req.db, customer_id=claims.get("sub", ""))
        ).customer
        if customer is None:
            return AuthResp.failure(error_code="unauthorized", error_message="Unknown customer")
        # Rotate: revoke the presented refresh token, then issue a fresh pair that
        # stays in the same family so the chain remains revocable end-to-end.
        self.revoked_token_dao.revoke(
            RevokeReq(db=req.db, jti=jti, expires_at=exp, reason="rotated", family_id=family_id or None)
        )
        tok = self.token_service.issue(
            IssueTokenReq(customer_id=customer.id, email=customer.email, family_id=family_id or None)
        )
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
        exp = int(claims.get("exp", 0))
        family_id = claims.get("fid", "")
        self.revoked_token_dao.revoke(
            RevokeReq(
                db=req.db, jti=claims.get("jti", ""),
                expires_at=exp, reason="logout", family_id=family_id or None,
            )
        )
        # Logging out kills the whole refresh chain for that session.
        if family_id:
            self.revoked_token_dao.revoke_family(
                RevokeFamilyReq(db=req.db, family_id=family_id, expires_at=exp, reason="logout")
            )
        req.db.commit()
        return LogoutResp()

    # ---------------- Password reset ----------------
    @observe("AuthFacade.request_password_reset", metric="customer.pwd_reset.request")
    def request_password_reset(self, req: RequestPasswordResetReq) -> MessageResp:
        customer = self.customer_dao.get_by_email(GetByEmailReq(db=req.db, email=req.email)).customer
        # Always report success — never reveal whether an email is registered.
        generic = MessageResp(message="If that email is registered, a reset link has been sent.")
        if customer is None:
            return generic
        token = create_access_token(
            subject=customer.id,
            token_type="pwd_reset",
            email=customer.email,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.password_reset_expire_minutes,
        )
        link = f"{settings.portal_base_url}{settings.password_reset_path}?token={token}"
        self.email_service.send(
            SendEmailReq(
                to=customer.email,
                subject="Reset your Image2Prompt password",
                body=(
                    "We received a request to reset your password.\n\n"
                    f"Reset it here (valid {settings.password_reset_expire_minutes} min):\n{link}\n\n"
                    "If you didn't request this, you can ignore this email."
                ),
            )
        )
        return generic

    @observe("AuthFacade.reset_password", metric="customer.pwd_reset.confirm")
    def reset_password(self, req: ResetPasswordReq) -> MessageResp:
        claims = self._consume_token(req.db, req.token, expected_typ="pwd_reset")
        if claims is None:
            return MessageResp.failure(error_code="unauthorized", error_message="Invalid or expired reset link")
        customer = self.customer_dao.get_by_id(
            GetByIdReq(db=req.db, customer_id=claims.get("sub", ""))
        ).customer
        if customer is None:
            return MessageResp.failure(error_code="unauthorized", error_message="Unknown customer")
        customer.password_hash = hash_password(req.new_password)
        # Single-use: revoke the reset token's jti so the link can't be replayed.
        self.revoked_token_dao.revoke(
            RevokeReq(db=req.db, jti=claims.get("jti", ""), expires_at=int(claims.get("exp", 0)), reason="pwd_reset")
        )
        self._audit(req.db, "customer.password_reset", actor_id=customer.id, actor_email=customer.email)
        req.db.commit()
        self.log.info("password reset for customer_id=%s", customer.id)
        return MessageResp(message="Your password has been reset. You can now sign in.")

    # ---------------- Email verification ----------------
    @observe("AuthFacade.send_verification_email", metric="customer.email_verify.send")
    def send_verification_email(self, req: SendVerificationReq) -> MessageResp:
        customer = self.customer_dao.get_by_id(
            GetByIdReq(db=req.db, customer_id=req.customer_id)
        ).customer
        if customer is None:
            return MessageResp.failure(error_code="not_found", error_message="Unknown customer")
        if customer.email_verified:
            return MessageResp(message="Email already verified.")
        token = create_access_token(
            subject=customer.id,
            token_type="email_verify",
            email=customer.email,
            secret=settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
            expire_minutes=settings.email_verify_expire_minutes,
        )
        link = f"{settings.portal_base_url}{settings.email_verify_path}?token={token}"
        self.email_service.send(
            SendEmailReq(
                to=customer.email,
                subject="Verify your Image2Prompt email",
                body=f"Confirm your email address:\n{link}\n",
            )
        )
        return MessageResp(message="Verification email sent.")

    @observe("AuthFacade.verify_email", metric="customer.email_verify.confirm")
    def verify_email(self, req: VerifyEmailReq) -> MessageResp:
        claims = self._consume_token(req.db, req.token, expected_typ="email_verify")
        if claims is None:
            return MessageResp.failure(error_code="unauthorized", error_message="Invalid or expired link")
        customer = self.customer_dao.get_by_id(
            GetByIdReq(db=req.db, customer_id=claims.get("sub", ""))
        ).customer
        if customer is None:
            return MessageResp.failure(error_code="unauthorized", error_message="Unknown customer")
        customer.email_verified = True
        self.revoked_token_dao.revoke(
            RevokeReq(db=req.db, jti=claims.get("jti", ""), expires_at=int(claims.get("exp", 0)), reason="email_verify")
        )
        self._audit(req.db, "customer.email_verified", actor_id=customer.id, actor_email=customer.email)
        req.db.commit()
        return MessageResp(message="Email verified.")

    def _consume_token(self, db, token: str, *, expected_typ: str):
        """Decode a single-use action token; return claims or None if invalid/used."""
        try:
            claims = decode_token(token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
        except jwt.PyJWTError:
            return None
        if claims.get("typ") != expected_typ:
            return None
        if self.revoked_token_dao.is_revoked(IsRevokedReq(db=db, jti=claims.get("jti", ""))).revoked:
            return None  # already used
        return claims
