"""Gateway smoke tests: rate limiting (429) and X-Request-ID correlation.

The proxy rate-limits before contacting upstreams, so 429 is deterministic even
with no services running."""

import os

os.environ["RATE_LIMIT_RPM"] = "3"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health_ok_and_not_rate_limited():
    for _ in range(10):
        assert client.get("/health").status_code == 200


def test_rate_limit_returns_429_after_threshold():
    # Public path (no auth needed); upstream is down so allowed requests 502,
    # but once over the limit the gateway returns 429 before any upstream call.
    statuses = [
        client.post("/api/customer/auth/login", json={"email": "a@b.io", "password": "x"}).status_code
        for _ in range(6)
    ]
    assert 429 in statuses
    # Everything before the limit is hit should not be 429.
    assert statuses[0] != 429


def test_request_id_is_echoed():
    r = client.get("/api/customer/me", headers={"X-Request-ID": "test-req-123"})
    # Auth fails (no token) but the correlation id is still echoed.
    assert r.headers.get("X-Request-ID") == "test-req-123"


def test_internal_paths_are_not_proxied():
    # Routes that strip their prefix (kb, customer) must not expose the upstream's
    # trusted /internal surface. The guard runs before auth, so the tell is 404
    # (blocked) vs 401 (missing token on a normal proxied path).
    assert client.get("/api/kb/internal/usage/customer/anyone").status_code == 404
    assert client.get("/api/customer/internal/customers/x").status_code == 404
    # A normal proxied path is not blocked by the guard (it proceeds to auth/rate
    # limiting — 401 or 429, never the guard's 404), proving the guard is specific.
    assert client.get("/api/kb/kbs").status_code != 404


def test_security_headers_present():
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"


def test_body_size_limit_returns_413(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_body_bytes", 5)
    r = client.post("/api/customer/auth/login", json={"email": "a@b.io", "password": "secret"})
    assert r.status_code == 413


def test_auth_endpoints_have_tighter_rate_limit(monkeypatch):
    from app.config import settings

    # General budget high, auth budget low: the auth limiter should trip first.
    monkeypatch.setattr(settings, "rate_limit_rpm", 1000)
    monkeypatch.setattr(settings, "auth_rate_limit_rpm", 2)
    statuses = [
        client.post("/api/customer/auth/login", json={"email": "a@b.io", "password": "x"}).status_code
        for _ in range(4)
    ]
    assert 429 in statuses
    # a non-auth path under the same client is not blocked by the auth limiter
    assert client.get("/health").status_code == 200


def test_rate_limiter_backends():
    import asyncio

    from app.ratelimit import MemoryRateLimiter, RedisRateLimiter, build_rate_limiter

    async def run():
        mem = MemoryRateLimiter()
        results = [await mem.over_limit("k", 2) for _ in range(3)]
        assert results == [False, False, True]  # 3rd hit exceeds limit of 2
        assert await mem.over_limit("k", 0) is False  # 0/negative limit disables

        # Redis backend with an unreachable server degrades to in-memory (never raises)
        rl = RedisRateLimiter("redis://127.0.0.1:6390/0")
        degraded = [await rl.over_limit("z", 1) for _ in range(2)]
        assert degraded == [False, True]

    asyncio.run(run())

    class _S:
        ratelimit_backend = "memory"
        redis_url = "redis://x"

    assert isinstance(build_rate_limiter(_S()), MemoryRateLimiter)
    _S.ratelimit_backend = "redis"
    assert isinstance(build_rate_limiter(_S()), RedisRateLimiter)


def test_csp_report_sink_accepts_reports():
    # The dedicated CSP-report route is public and bypasses the proxy/auth.
    r = client.post("/api/csp-report", json={"csp-report": {"violated-directive": "img-src 'self'"}})
    assert r.status_code == 204
    # A malformed body must still not error.
    r2 = client.post("/api/csp-report", content=b"not-json")
    assert r2.status_code == 204
