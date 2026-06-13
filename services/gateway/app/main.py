"""API gateway / BFF.

Single edge for both portals. Validates the JWT at the edge (public routes
excepted) and reverse-proxies to the backing microservice based on path prefix:

  /api/admin/*     -> admin-service       (target: /admin/*)
  /api/customer/*  -> customer-service     (target: /*)
  /api/images/*    -> image-processing      (target: /*)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import httpx
import jwt
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from image2prompt_shared.logging_config import configure_logging, get_logger
from image2prompt_shared.observability import Metrics, init_observability, instrument_fastapi
from image2prompt_shared.request_context import RequestIdMiddleware, get_request_id
from image2prompt_shared.security import decode_token

from .config import settings

configure_logging(service_name=settings.service_name, level=settings.log_level, as_json=settings.log_json)
init_observability(settings)
log = get_logger(__name__)


@dataclass
class Route:
    prefix: str
    base_url: str
    rewrite: Callable[[str], str]


ROUTES: list[Route] = [
    Route("/api/admin", settings.admin_service_url, lambda p: "/admin" + p[len("/api/admin"):]),
    Route("/api/customer", settings.customer_service_url, lambda p: p[len("/api/customer"):] or "/"),
    Route("/api/images", settings.image_service_url, lambda p: p[len("/api/images"):] or "/"),
]

# Routes that do not require a valid JWT.
PUBLIC_PATHS = {
    "/api/admin/auth/login",
    "/api/admin/auth/refresh",
    "/api/customer/auth/login",
    "/api/customer/auth/signup",
    "/api/customer/auth/refresh",
    "/api/customer/auth/logout",
    "/api/admin/auth/logout",
    "/health",
}

# Headers we must not forward verbatim.
_HOP_BY_HOP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}

app = FastAPI(title="Image2Prompt Gateway")
instrument_fastapi(app)
app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "gateway"}


def _match_route(path: str) -> Route | None:
    for route in ROUTES:
        if path == route.prefix or path.startswith(route.prefix + "/"):
            return route
    return None


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS


# Fixed-window in-memory rate limiter. Key = JWT subject if present, else client IP.
_RATE_WINDOWS: dict[tuple[str, int], int] = {}


def _rate_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = decode_token(auth[7:], secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
            return f"sub:{payload.get('sub')}"
        except jwt.PyJWTError:
            pass
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _rate_limited(key: str) -> bool:
    if not settings.rate_limit_enabled:
        return False
    window = int(time.time() // 60)
    bucket = (key, window)
    _RATE_WINDOWS[bucket] = _RATE_WINDOWS.get(bucket, 0) + 1
    if len(_RATE_WINDOWS) > 10000:  # opportunistic cleanup of old windows
        for k in [k for k in _RATE_WINDOWS if k[1] != window]:
            _RATE_WINDOWS.pop(k, None)
    return _RATE_WINDOWS[bucket] > settings.rate_limit_rpm


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(full_path: str, request: Request) -> Response:
    path = request.url.path
    request_id = get_request_id()  # set by RequestIdMiddleware (incoming header or generated)

    route = _match_route(path)
    if route is None:
        return JSONResponse(
            status_code=404, content={"detail": "No matching gateway route"},
            headers={"X-Request-ID": request_id},
        )

    # Rate limit first (deterministic regardless of upstream/auth).
    if _rate_limited(_rate_key(request)):
        Metrics.counter_add("gateway.rate_limited", 1, {"prefix": route.prefix})
        return JSONResponse(
            status_code=429, content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60", "X-Request-ID": request_id},
        )

    # Edge auth check (public routes excepted).
    if not _is_public(path):
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        if not token:
            return JSONResponse(
                status_code=401, content={"detail": "Missing bearer token"},
                headers={"X-Request-ID": request_id},
            )
        try:
            decode_token(token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
        except jwt.PyJWTError:
            return JSONResponse(
                status_code=401, content={"detail": "Invalid or expired token"},
                headers={"X-Request-ID": request_id},
            )

    target_url = route.base_url + route.rewrite(path)
    body = await request.body()
    fwd_headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
    fwd_headers["X-Request-ID"] = request_id  # propagate correlation id downstream

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            upstream = await client.request(
                request.method,
                target_url,
                params=dict(request.query_params),
                content=body,
                headers=fwd_headers,
            )
        except httpx.HTTPError as exc:
            return JSONResponse(status_code=502, content={"detail": f"Upstream error: {exc}"})

    Metrics.counter_add(
        "gateway.proxy", 1, {"prefix": route.prefix, "status": str(upstream.status_code)}
    )
    log.info("proxy %s %s -> %s [%s] req_id=%s", request.method, path, target_url, upstream.status_code, request_id)
    resp_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP
    }
    resp_headers["X-Request-ID"] = request_id
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=resp_headers,
        media_type=upstream.headers.get("content-type"),
    )
