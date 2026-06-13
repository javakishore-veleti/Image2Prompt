"""Request correlation id propagated via a contextvar + an ASGI middleware.

The gateway generates ``X-Request-ID`` and forwards it; every service runs
``RequestIdMiddleware`` to capture it into a contextvar so it appears on logs and
is echoed back on the response. Logs across services share the same id.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str) -> None:
    _request_id.set(value)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        _request_id.set(rid)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = rid
        return response
