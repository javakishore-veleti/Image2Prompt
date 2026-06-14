"""DI container for kb-service. Singletons wired via constructor injection."""

from __future__ import annotations

from .dao.kb_dao import KbDao
from .facades.interfaces import IKbFacade
from .facades.kb_facade import KbFacade
from .services.clients import GenerationClient, SubscriptionClient
from .services.embedder import build_embedder

_kb_dao = KbDao()
_embedder = build_embedder()
_subscription_client = SubscriptionClient()
_generation_client = GenerationClient()

_kb_facade: IKbFacade = KbFacade(
    kb_dao=_kb_dao,
    embedder=_embedder,
    subscription_client=_subscription_client,
    generation_client=_generation_client,
)


def get_kb_facade() -> IKbFacade:
    return _kb_facade
