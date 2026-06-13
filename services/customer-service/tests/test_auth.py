"""Smoke test for customer-service auth using an in-memory SQLite DB."""

import os
import tempfile

# File-based SQLite so every pooled connection sees the same tables
# (in-memory SQLite gives each connection its own private database).
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_signup_login_me():
    with TestClient(app) as client:
        # signup
        r = client.post(
            "/auth/signup",
            json={"email": "alice@example.com", "password": "pw123456", "name": "Alice"},
        )
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        assert token

        # duplicate signup rejected
        r2 = client.post(
            "/auth/signup", json={"email": "alice@example.com", "password": "pw123456"}
        )
        assert r2.status_code == 409

        # login
        r3 = client.post(
            "/auth/login", json={"email": "alice@example.com", "password": "pw123456"}
        )
        assert r3.status_code == 200, r3.text

        # /me with bearer
        r4 = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert r4.status_code == 200
        assert r4.json()["email"] == "alice@example.com"

        # default preferences created
        r5 = client.get("/me/preferences", headers={"Authorization": f"Bearer {token}"})
        assert r5.status_code == 200
        assert r5.json()["storage_backend"] == "local"


def test_internal_customer_search():
    with TestClient(app) as client:
        client.post(
            "/auth/signup", json={"email": "bob@example.com", "password": "pw123456", "name": "Bob"}
        )
        r = client.get("/internal/customers", params={"search": "bob"})
        assert r.status_code == 200
        assert any(c["email"] == "bob@example.com" for c in r.json())


def test_connections_flow():
    with TestClient(app) as client:
        tok = client.post(
            "/auth/signup", json={"email": "conn@example.com", "password": "pw123456"}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        # connect a mock Google Drive
        r = client.post("/me/connections", json={"provider": "google_drive"}, headers=h)
        assert r.status_code == 201, r.text
        conn = r.json()
        assert conn["provider"] == "google_drive" and conn["status"] == "connected"

        # list connections
        assert len(client.get("/me/connections", headers=h).json()) == 1

        # mock files + search
        files = client.get(f"/me/connections/{conn['id']}/files", headers=h).json()
        assert len(files) >= 1
        filtered = client.get(
            f"/me/connections/{conn['id']}/files", params={"search": "sunset"}, headers=h
        ).json()
        assert all("sunset" in f["name"].lower() for f in filtered)

        # disconnect
        assert client.delete(f"/me/connections/{conn['id']}", headers=h).status_code == 204
        assert client.get("/me/connections", headers=h).json() == []


def test_billing_without_stripe_is_graceful():
    with TestClient(app) as client:
        tok = client.post(
            "/auth/signup", json={"email": "bill@example.com", "password": "pw123456"}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        ps = client.get("/me/payment-settings", headers=h).json()
        assert ps["stripe_configured"] is False  # no STRIPE_API_KEY in tests

        billing = client.get("/me/billing", headers=h).json()
        assert billing["configured"] is False
        assert billing["receipts"] == []

        si = client.post("/me/payment-settings/setup-intent", headers=h).json()
        assert si["configured"] is False and si["client_secret"] is None


def test_refresh_token_flow():
    with TestClient(app) as client:
        signup = client.post(
            "/auth/signup", json={"email": "refresh@example.com", "password": "pw123456"}
        ).json()
        assert signup["refresh_token"]
        # exchange refresh for a new access token
        r = client.post("/auth/refresh", json={"refresh_token": signup["refresh_token"]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["access_token"] and body["refresh_token"]
        # the new access token works
        me = client.get("/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.status_code == 200

        # an access token is NOT accepted as a refresh token
        bad = client.post("/auth/refresh", json={"refresh_token": signup["access_token"]})
        assert bad.status_code == 401
