"""Dependency-injection container.

Instantiates the singleton layer components once and wires dependencies
(constructor injection). Controllers receive facades via their *interface* using
the provider functions below (used with FastAPI ``Depends``).
"""

from __future__ import annotations

from .dao.audit_dao import AuditDao
from .dao.billing_dao import BillingDao
from .dao.connection_dao import ConnectionDao
from .dao.customer_dao import CustomerDao
from .dao.payment_dao import PaymentDao
from .dao.preference_dao import PreferenceDao
from .dao.project_dao import ProjectDao
from .dao.revoked_token_dao import RevokedTokenDao
from .facades.auth_facade import AuthFacade
from .facades.connections_facade import ConnectionsFacade
from .facades.interfaces import (
    IAuthFacade,
    IConnectionsFacade,
    IInternalFacade,
    IPaymentsFacade,
    IProfileFacade,
    IProjectsFacade,
)
from .facades.internal_facade import InternalFacade
from .facades.payments_facade import PaymentsFacade
from .facades.profile_facade import ProfileFacade
from .facades.projects_facade import ProjectsFacade
from .services.billing_clients import BillingClient
from .services.connection_provider_service import ConnectionProviderService
from .services.email_service import EmailService
from .services.google_drive_service import GoogleDriveService
from .services.onedrive_service import OneDriveService
from .services.stripe_service import StripeService
from .services.token_service import TokenService

# --- DAOs ---
_customer_dao = CustomerDao()
_preference_dao = PreferenceDao()
_project_dao = ProjectDao()
_payment_dao = PaymentDao()
_connection_dao = ConnectionDao()
_revoked_token_dao = RevokedTokenDao()
_audit_dao = AuditDao()
_billing_dao = BillingDao()

# --- Services ---
_token_service = TokenService()
_connection_provider_service = ConnectionProviderService()
_google_drive_service = GoogleDriveService()
_onedrive_service = OneDriveService()
_stripe_service = StripeService()
_email_service = EmailService()
_billing_client = BillingClient()

# --- Facades (wired against interfaces) ---
_auth_facade: IAuthFacade = AuthFacade(
    customer_dao=_customer_dao,
    preference_dao=_preference_dao,
    token_service=_token_service,
    revoked_token_dao=_revoked_token_dao,
    email_service=_email_service,
    audit_dao=_audit_dao,
)
_profile_facade: IProfileFacade = ProfileFacade(
    customer_dao=_customer_dao, preference_dao=_preference_dao, audit_dao=_audit_dao
)
_projects_facade: IProjectsFacade = ProjectsFacade(project_dao=_project_dao)
_payments_facade: IPaymentsFacade = PaymentsFacade(
    payment_dao=_payment_dao,
    customer_dao=_customer_dao,
    stripe_service=_stripe_service,
    billing_client=_billing_client,
    billing_dao=_billing_dao,
)
_internal_facade: IInternalFacade = InternalFacade(
    customer_dao=_customer_dao, preference_dao=_preference_dao
)
_connections_facade: IConnectionsFacade = ConnectionsFacade(
    connection_dao=_connection_dao,
    customer_dao=_customer_dao,
    provider_service=_connection_provider_service,
    google_drive_service=_google_drive_service,
    onedrive_service=_onedrive_service,
    audit_dao=_audit_dao,
)


# Provider functions for FastAPI Depends (return the interface type).
def get_auth_facade() -> IAuthFacade:
    return _auth_facade


def get_profile_facade() -> IProfileFacade:
    return _profile_facade


def get_projects_facade() -> IProjectsFacade:
    return _projects_facade


def get_payments_facade() -> IPaymentsFacade:
    return _payments_facade


def get_internal_facade() -> IInternalFacade:
    return _internal_facade


def get_connections_facade() -> IConnectionsFacade:
    return _connections_facade
