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
