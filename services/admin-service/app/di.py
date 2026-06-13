"""DI container for admin-service. Singletons wired via constructor injection."""

from __future__ import annotations

from .dao.admin_user_dao import AdminUserDao
from .dao.csp_violation_dao import CspViolationDao
from .dao.provider_dao import ProviderDao
from .dao.revoked_token_dao import RevokedTokenDao
from .facades.admin_users_facade import AdminUsersFacade
from .facades.analytics_facade import AnalyticsFacade
from .facades.auth_facade import AdminAuthFacade
from .facades.csp_facade import CspFacade
from .facades.customers_facade import CustomersFacade
from .facades.interfaces import (
    IAdminAuthFacade,
    IAdminUsersFacade,
    IAnalyticsFacade,
    ICspFacade,
    ICustomersFacade,
    IProvidersFacade,
)
from .facades.providers_facade import ProvidersFacade
from .services.analytics_service import AnalyticsService
from .services.customer_directory_service import CustomerDirectoryService
from .services.token_service import AdminTokenService

# DAOs
_admin_user_dao = AdminUserDao()
_provider_dao = ProviderDao()
_revoked_token_dao = RevokedTokenDao()
_csp_violation_dao = CspViolationDao()

# Services
_token_service = AdminTokenService()
_directory_service = CustomerDirectoryService()
_analytics_service = AnalyticsService()

# Facades (wired against interfaces)
_auth_facade: IAdminAuthFacade = AdminAuthFacade(
    admin_user_dao=_admin_user_dao, token_service=_token_service, revoked_token_dao=_revoked_token_dao
)
_providers_facade: IProvidersFacade = ProvidersFacade(provider_dao=_provider_dao)
_customers_facade: ICustomersFacade = CustomersFacade(directory_service=_directory_service)
_analytics_facade: IAnalyticsFacade = AnalyticsFacade(
    provider_dao=_provider_dao, analytics_service=_analytics_service
)
_admin_users_facade: IAdminUsersFacade = AdminUsersFacade(admin_user_dao=_admin_user_dao)
_csp_facade: ICspFacade = CspFacade(csp_violation_dao=_csp_violation_dao)


def get_auth_facade() -> IAdminAuthFacade:
    return _auth_facade


def get_csp_facade() -> ICspFacade:
    return _csp_facade


def get_providers_facade() -> IProvidersFacade:
    return _providers_facade


def get_customers_facade() -> ICustomersFacade:
    return _customers_facade


def get_analytics_facade() -> IAnalyticsFacade:
    return _analytics_facade


def get_admin_users_facade() -> IAdminUsersFacade:
    return _admin_users_facade
