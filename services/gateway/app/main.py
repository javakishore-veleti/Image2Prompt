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
from starlette.middleware.base import BaseHTTPMiddleware

from image2prompt_shared.logging_config import configure_logging, get_logger
from image2prompt_shared.observability import Metrics, init_observability, instrument_fastapi
from image2prompt_shared.request_context import RequestIdMiddleware, get_request_id
from image2prompt_shared.security import decode_token

from .config import settings
from .ratelimit import build_rate_limiter

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
    Route("/api/kb", settings.kb_service_url, lambda p: p[len("/api/kb"):] or "/"),
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
    "/api/customer/auth/forgot-password",
    "/api/customer/auth/reset-password",
    "/api/customer/auth/verify-email",
    "/api/customer/me/connections/google/callback",
    "/api/customer/me/connections/onedrive/callback",
    "/health",
}

# Headers we must not forward verbatim.
_HOP_BY_HOP = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-Permitted-Cross-Domain-Policies": "none",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    """Caps request body size (413) and adds hardening headers to responses."""

    async def dispatch(self, request: Request, call_next):
        limit = settings.max_body_bytes
        if limit > 0:
            cl = request.headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > limit:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        response = await call_next(request)
        if settings.security_headers_enabled:
            for k, v in _SECURITY_HEADERS.items():
                response.headers.setdefault(k, v)
            if settings.hsts_enabled:
                response.headers.setdefault(
                    "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
                )
        return response


app = FastAPI(title="Image2Prompt Gateway")
instrument_fastapi(app)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Request-ID"],
)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "gateway"}


def _normalize_csp_reports(payload, user_agent: str) -> list[dict]:
    """Normalize both legacy report-uri (`{"csp-report": {...}}`) and modern
    Reporting-API (`[{"type":"csp-violation","body":{...}}]`) payloads into the
    flat shape admin-service ingests."""
    reports: list[dict] = []
    if isinstance(payload, dict) and isinstance(payload.get("csp-report"), dict):
        r = payload["csp-report"]
        reports.append({
            "document_uri": r.get("document-uri"),
            "violated_directive": r.get("violated-directive") or r.get("effective-directive"),
            "blocked_uri": r.get("blocked-uri"),
            "source_file": r.get("source-file"),
            "line_number": r.get("line-number"),
            "disposition": r.get("disposition"),
            "user_agent": user_agent,
            "raw": r,
        })
    elif isinstance(payload, list):
        for item in payload[:20]:  # cap per request
            if not isinstance(item, dict):
                continue
            if item.get("type") and item.get("type") != "csp-violation":
                continue
            b = item.get("body") or {}
            reports.append({
                "document_uri": b.get("documentURL") or b.get("document-uri"),
                "violated_directive": b.get("effectiveDirective") or b.get("violatedDirective"),
                "blocked_uri": b.get("blockedURL") or b.get("blocked-uri"),
                "source_file": b.get("sourceFile"),
                "line_number": b.get("lineNumber"),
                "disposition": b.get("disposition"),
                "user_agent": item.get("user_agent") or user_agent,
                "raw": item,
            })
    return reports


@app.post("/api/csp-report", include_in_schema=False)
async def csp_report(request: Request) -> Response:
    """Sink for browser CSP violation reports (the portals' report-uri / report-to).

    Public, best-effort: parse, log, forward to admin-service for the dashboard,
    always 204, never raises. Accepts both `application/csp-report` and the
    Reporting-API `application/reports+json` payloads.
    """
    # Rate-limit per client so a noisy/abusive policy can't flood the sink.
    if await _rate_limited(_rate_key(request)):
        return Response(status_code=204)
    try:
        import json

        raw = (await request.body()).decode("utf-8", "replace")
        if not raw:
            return Response(status_code=204)
        log.warning("csp-violation %s", raw[:4000])
        Metrics.counter_add("gateway.csp_report", 1)
        reports = _normalize_csp_reports(json.loads(raw), request.headers.get("user-agent", ""))
        if reports:
            url = f"{settings.admin_service_url}/internal/csp-violations"
            async with httpx.AsyncClient(timeout=5.0) as client:
                for rpt in reports:
                    try:
                        await client.post(url, json=rpt)
                    except httpx.HTTPError:
                        pass  # dashboard ingest is best-effort
    except Exception:  # a malformed report must never error the edge
        pass
    return Response(status_code=204)


def _match_route(path: str) -> Route | None:
    for route in ROUTES:
        if path == route.prefix or path.startswith(route.prefix + "/"):
            return route
    return None


def _is_public(path: str) -> bool:
    return path in PUBLIC_PATHS


# Pluggable rate limiter (memory or redis; see ratelimit.py). Key = JWT subject
# if present, else client IP.
_LIMITER = build_rate_limiter(settings)


def _rate_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = decode_token(auth[7:], secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
            return f"sub:{payload.get('sub')}"
        except jwt.PyJWTError:
            pass
    return f"ip:{request.client.host if request.client else 'unknown'}"


# Unauthenticated auth endpoints get a tighter per-IP budget (credential-stuffing).
AUTH_SENSITIVE_PATHS = {
    "/api/customer/auth/login",
    "/api/customer/auth/signup",
    "/api/customer/auth/forgot-password",
    "/api/customer/auth/reset-password",
    "/api/admin/auth/login",
}


async def _rate_limited(key: str, limit: int | None = None) -> bool:
    if not settings.rate_limit_enabled:
        return False
    cap = settings.rate_limit_rpm if limit is None else limit
    return await _LIMITER.over_limit(key, cap)


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
    if await _rate_limited(_rate_key(request)):
        Metrics.counter_add("gateway.rate_limited", 1, {"prefix": route.prefix})
        return JSONResponse(
            status_code=429, content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60", "X-Request-ID": request_id},
        )

    # Tighter per-IP budget on unauthenticated auth endpoints.
    if path in AUTH_SENSITIVE_PATHS:
        ip = request.client.host if request.client else "unknown"
        if await _rate_limited(f"auth:{path}:{ip}", settings.auth_rate_limit_rpm):
            Metrics.counter_add("gateway.auth_rate_limited", 1, {"path": path})
            return JSONResponse(
                status_code=429, content={"detail": "Too many attempts; please wait and retry."},
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
