"""Smoke test for admin-service: seeded admin login + provider seed/toggle."""

import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"
os.environ["ADMIN_EMAIL"] = "admin@test.io"
os.environ["ADMIN_PASSWORD"] = "admin12345"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _login(client) -> str:
    r = client.post(
        "/admin/auth/login", json={"email": "admin@test.io", "password": "admin12345"}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_login_and_providers_seeded():
    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}

        # providers seeded; bedrock + mock enabled by default
        r = client.get("/admin/providers", headers=h)
        assert r.status_code == 200
        providers = {p["key"]: p for p in r.json()}
        assert providers["bedrock"]["enabled"] is True
        assert providers["mock"]["enabled"] is True
        assert providers["openai"]["enabled"] is False

        # internal enabled-only listing used by image-processing
        r2 = client.get("/internal/providers", params={"enabled": "true"})
        keys = {p["key"] for p in r2.json()}
        assert "bedrock" in keys and "openai" not in keys

        # toggle openai on
        oid = providers["openai"]["id"]
        r3 = client.patch(f"/admin/providers/{oid}", json={"enabled": True}, headers=h)
        assert r3.status_code == 200 and r3.json()["enabled"] is True


def test_login_rejects_bad_password():
    with TestClient(app) as client:
        r = client.post(
            "/admin/auth/login", json={"email": "admin@test.io", "password": "wrong"}
        )
        assert r.status_code == 401


def test_admin_refresh_flow():
    with TestClient(app) as client:
        login = client.post(
            "/admin/auth/login", json={"email": "admin@test.io", "password": "admin12345"}
        ).json()
        assert login["refresh_token"]
        r = client.post("/admin/auth/refresh", json={"refresh_token": login["refresh_token"]})
        assert r.status_code == 200 and r.json()["access_token"]
        bad = client.post("/admin/auth/refresh", json={"refresh_token": login["access_token"]})
        assert bad.status_code == 401
