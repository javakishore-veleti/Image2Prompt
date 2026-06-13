"""DI container for admin-service. Singletons wired via constructor injection."""

from __future__ import annotations

from .dao.admin_user_dao import AdminUserDao
from .dao.provider_dao import ProviderDao
from .facades.auth_facade import AdminAuthFacade
from .facades.customers_facade import CustomersFacade
from .facades.interfaces import IAdminAuthFacade, ICustomersFacade, IProvidersFacade
from .facades.providers_facade import ProvidersFacade
from .services.customer_directory_service import CustomerDirectoryService
from .services.token_service import AdminTokenService

# DAOs
_admin_user_dao = AdminUserDao()
_provider_dao = ProviderDao()

# Services
_token_service = AdminTokenService()
_directory_service = CustomerDirectoryService()

# Facades (wired against interfaces)
_auth_facade: IAdminAuthFacade = AdminAuthFacade(
    admin_user_dao=_admin_user_dao, token_service=_token_service
)
_providers_facade: IProvidersFacade = ProvidersFacade(provider_dao=_provider_dao)
_customers_facade: ICustomersFacade = CustomersFacade(directory_service=_directory_service)


def get_auth_facade() -> IAdminAuthFacade:
    return _auth_facade


def get_providers_facade() -> IProvidersFacade:
    return _providers_facade


def get_customers_facade() -> ICustomersFacade:
    return _customers_facade
