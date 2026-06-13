"""img2pmpt-caf-routers — Common Application Framework: LLM routers.

Consumers use the ``client`` sub-package (``IRouterClient`` / ``RouterClient``)
to ``route`` an image+instruction to a named router (``openrouter`` / ``litellm``)
and stay agnostic to the SDK behind it. Each router is a feature-toggled
implementation in ``provider_impls``; SDKs are imported lazily and failures come
back as a failed ``*Resp`` rather than raising.
"""

from .client.dtos import RouteReq, RouteResp
from .client.interfaces import IRouterClient
from .client.router_client import RouterClient, get_router_client

__version__ = "0.1.0"

__all__ = [
    "RouteReq",
    "RouteResp",
    "IRouterClient",
    "RouterClient",
    "get_router_client",
]
