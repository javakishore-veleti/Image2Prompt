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
