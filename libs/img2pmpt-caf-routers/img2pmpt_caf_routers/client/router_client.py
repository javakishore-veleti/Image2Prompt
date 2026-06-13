"""The client consumers use. Resolves the requested router, enforces its feature
toggle, and delegates. Never raises on a router failure — returns a failed
``RouteResp`` so callers stay robust."""

from __future__ import annotations

import threading

from ..config import CafRoutersSettings
from ..provider_impls.factory import build_providers
from .dtos import RouteReq, RouteResp, RouterInfo
from .interfaces import IRouterClient


class RouterClient(IRouterClient):
    def __init__(self, settings: CafRoutersSettings | None = None) -> None:
        self._settings = settings or CafRoutersSettings()
        self._providers = build_providers(self._settings)

    def available(self) -> list[RouterInfo]:
        return [
            RouterInfo(name=name, enabled=self._settings.enabled_for(name))
            for name in self._providers
        ]

    def route(self, req: RouteReq) -> RouteResp:
        provider = self._providers.get(req.router)
        if provider is None:
            return RouteResp(
                success=False, router=req.router, error_code="unknown_router",
                error_message=f"Unknown router: {req.router!r}",
            )
        if not self._settings.enabled_for(req.router):
            return RouteResp(
                success=False, router=req.router, error_code="router_disabled",
                error_message=f"Router '{req.router}' is disabled "
                f"(CAF_ROUTERS_{req.router.upper()}_ENABLED=false)",
            )
        try:
            return provider.route(req)
        except Exception as exc:  # defense in depth; providers already guard
            return RouteResp(success=False, router=req.router, error_code="provider_error", error_message=str(exc))


_default_client: RouterClient | None = None
_lock = threading.Lock()


def get_router_client() -> RouterClient:
    """Process-wide singleton router client."""
    global _default_client
    if _default_client is None:
        with _lock:
            if _default_client is None:
                _default_client = RouterClient()
    return _default_client
