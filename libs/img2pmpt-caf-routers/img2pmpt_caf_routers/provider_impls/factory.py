"""Builds the name -> router provider registry."""

from __future__ import annotations

from ..config import CafRoutersSettings
from .interfaces import IRouterProvider
from .litellm_provider import LiteLLMProvider
from .openrouter_provider import OpenRouterProvider


def build_providers(settings: CafRoutersSettings) -> dict[str, IRouterProvider]:
    providers: list[IRouterProvider] = [
        OpenRouterProvider(settings),
        LiteLLMProvider(settings),
    ]
    return {p.name: p for p in providers}
