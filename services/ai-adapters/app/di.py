"""DI container for ai-adapters."""

from __future__ import annotations

from .facades.interfaces import IInvokeFacade
from .facades.invoke_facade import InvokeFacade
from .registry import REGISTRY
from .services.invoke_service import InvokeService

_invoke_service = InvokeService(registry=REGISTRY)
_invoke_facade: IInvokeFacade = InvokeFacade(invoke_service=_invoke_service, registry=REGISTRY)


def get_invoke_facade() -> IInvokeFacade:
    return _invoke_facade
