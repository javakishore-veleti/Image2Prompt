"""Dependency-injection container.

Instantiates the singleton layer components once and wires dependencies
(constructor injection). Controllers receive facades via their *interface* using
the provider functions below (used with FastAPI ``Depends``).
"""

from __future__ import annotations

from .dao.customer_dao import CustomerDao
from .dao.payment_dao import PaymentDao
from .dao.preference_dao import PreferenceDao
from .dao.project_dao import ProjectDao
from .facades.auth_facade import AuthFacade
from .facades.interfaces import (
    IAuthFacade,
    IInternalFacade,
    IPaymentsFacade,
    IProfileFacade,
    IProjectsFacade,
)
from .facades.internal_facade import InternalFacade
from .facades.payments_facade import PaymentsFacade
from .facades.profile_facade import ProfileFacade
from .facades.projects_facade import ProjectsFacade
from .services.token_service import TokenService

# --- DAOs ---
_customer_dao = CustomerDao()
_preference_dao = PreferenceDao()
_project_dao = ProjectDao()
_payment_dao = PaymentDao()

# --- Services ---
_token_service = TokenService()

# --- Facades (wired against interfaces) ---
_auth_facade: IAuthFacade = AuthFacade(
    customer_dao=_customer_dao, preference_dao=_preference_dao, token_service=_token_service
)
_profile_facade: IProfileFacade = ProfileFacade(
    customer_dao=_customer_dao, preference_dao=_preference_dao
)
_projects_facade: IProjectsFacade = ProjectsFacade(project_dao=_project_dao)
_payments_facade: IPaymentsFacade = PaymentsFacade(payment_dao=_payment_dao)
_internal_facade: IInternalFacade = InternalFacade(
    customer_dao=_customer_dao, preference_dao=_preference_dao
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
