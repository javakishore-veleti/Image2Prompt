"""Base classes for the layered, shared-nothing architecture.

Flow: API controller -> Facade -> Service -> DAO.

- Controllers depend on facade *interfaces* (ABCs), resolved via the DI container.
- Facades orchestrate a use case; Services are focused, reusable (e.g. CRUD)
  components; DAOs do DB access only.
- Every component is a stateless singleton (see SingletonMeta). All inputs/outputs
  are ``*Req`` / ``*Resp`` objects — methods never take loose positional args.
"""

from __future__ import annotations

from abc import ABC

from .logging_config import get_logger
from .singleton import SingletonMeta


class _Singleton(metaclass=SingletonMeta):
    pass


class BaseComponent(_Singleton):
    """Common base: a logger and singleton identity. Holds no per-request state."""

    def __init__(self) -> None:
        self.log = get_logger(self.__class__.__module__ + "." + self.__class__.__name__)


class BaseDao(BaseComponent):
    """DB access only. Receives a SQLAlchemy Session inside its ``*Req``."""


class BaseService(BaseComponent):
    """Focused, reusable logic (e.g. CRUD). Depends on DAOs."""


class BaseFacade(BaseComponent):
    """Use-case orchestration. Depends on services/DAOs. Exposed to controllers
    via an interface (subclass both this and the interface ABC)."""


class FacadeInterface(ABC):
    """Marker base for facade interfaces that controllers are wired against."""
