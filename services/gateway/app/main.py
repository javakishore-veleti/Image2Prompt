"""API gateway / BFF.

Single edge for both portals. Validates the JWT at the edge (public routes
excepted) and reverse-proxies to the backing microservice based on path prefix:

  /api/admin/*     -> admin-service       (target: /admin/*)
  /api/customer/*  -> customer-service     (target: /*)
  /api/images/*    -> image-processing      (target: /*)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import httpx
import jwt
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from image2prompt_shared.logging_config import configure_logging, get_logger
from image2prompt_shared.observability import Metrics, init_observability, instrument_fastapi
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
    "/api/customer/auth/login",
    "/api/customer/auth/signup",
    "/health",
}

# Headers we must not forward verbatim.
_HOP_BY_HOP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}

app = FastAPI(title="Image2Prompt Gateway")
instrument_fastapi(app)

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


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(full_path: str, request: Request) -> Response:
    path = request.url.path
    route = _match_route(path)
    if route is None:
        return JSONResponse(status_code=404, content={"detail": "No matching gateway route"})

    # Edge auth check (public routes excepted).
    if not _is_public(path):
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Missing bearer token"})
        try:
            decode_token(token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
        except jwt.PyJWTError:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

    target_url = route.base_url + route.rewrite(path)
    body = await request.body()
    fwd_headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}

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
    log.info("proxy %s %s -> %s [%s]", request.method, path, target_url, upstream.status_code)
    resp_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=resp_headers,
        media_type=upstream.headers.get("content-type"),
    )
