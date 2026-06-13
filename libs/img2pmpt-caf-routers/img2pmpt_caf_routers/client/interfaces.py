"""The interface consumers depend on (never a provider directly)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .dtos import RouteReq, RouteResp


class IRouterClient(ABC):
    @abstractmethod
    def route(self, req: RouteReq) -> RouteResp: ...
