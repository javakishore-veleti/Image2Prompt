"""Smoke test for customer-service auth using an in-memory SQLite DB."""

import os
import tempfile

# File-based SQLite so every pooled connection sees the same tables
# (in-memory SQLite gives each connection its own private database).
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"
os.environ["SCHEDULER_ENABLED"] = "false"

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


def test_internal_download_mock_connection_returns_placeholder_png():
    with TestClient(app) as client:
        tok = client.post(
            "/auth/signup", json={"email": "dl@example.com", "password": "pw123456"}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        conn = client.post(
            "/me/connections", json={"provider": "google_drive"}, headers=h
        ).json()
        cust = client.get("/me", headers=h).json()

        # internal content endpoint (used by image-processing) -> placeholder PNG bytes
        r = client.get(
            f"/internal/customers/{cust['id']}/connections/{conn['id']}/files/any-file/content"
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("image/png")
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


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


def test_request_id_echoed_by_service():
    with TestClient(app) as client:
        r = client.get("/health", headers={"X-Request-ID": "svc-rid-9"})
        assert r.headers.get("X-Request-ID") == "svc-rid-9"
        # generated when absent
        r2 = client.get("/health")
        assert r2.headers.get("X-Request-ID")


def test_logout_revokes_refresh_token():
    with TestClient(app) as client:
        s = client.post(
            "/auth/signup", json={"email": "revoke@example.com", "password": "pw123456"}
        ).json()
        # logout revokes the refresh token
        assert client.post("/auth/logout", json={"refresh_token": s["refresh_token"]}).status_code == 204
        # the revoked refresh token can no longer mint access tokens
        assert client.post("/auth/refresh", json={"refresh_token": s["refresh_token"]}).status_code == 401


def test_refresh_rotation_blocks_reuse():
    with TestClient(app) as client:
        s = client.post(
            "/auth/signup", json={"email": "rotate@example.com", "password": "pw123456"}
        ).json()
        first = client.post("/auth/refresh", json={"refresh_token": s["refresh_token"]})
        assert first.status_code == 200
        # reusing the now-rotated refresh token is rejected
        reuse = client.post("/auth/refresh", json={"refresh_token": s["refresh_token"]})
        assert reuse.status_code == 401


def test_refresh_reuse_revokes_whole_family():
    """Reuse of a rotated token is treated as theft: the entire token family
    (including the legitimately-rotated descendant) is revoked."""
    with TestClient(app) as client:
        s = client.post(
            "/auth/signup", json={"email": "family@example.com", "password": "pw123456"}
        ).json()
        first = client.post("/auth/refresh", json={"refresh_token": s["refresh_token"]})
        assert first.status_code == 200
        live = first.json()["refresh_token"]
        # attacker replays the old (rotated) token -> reuse detected
        assert client.post("/auth/refresh", json={"refresh_token": s["refresh_token"]}).status_code == 401
        # the once-valid descendant is now dead too (family burned)
        assert client.post("/auth/refresh", json={"refresh_token": live}).status_code == 401


def test_logout_revokes_whole_family():
    with TestClient(app) as client:
        s = client.post(
            "/auth/signup", json={"email": "famlogout@example.com", "password": "pw123456"}
        ).json()
        rotated = client.post("/auth/refresh", json={"refresh_token": s["refresh_token"]}).json()
        # logout with the current token kills the family
        assert client.post("/auth/logout", json={"refresh_token": rotated["refresh_token"]}).status_code == 204
        # any descendant token from the same login is rejected
        assert client.post("/auth/refresh", json={"refresh_token": rotated["refresh_token"]}).status_code == 401


def test_forgot_password_is_generic_and_resets(monkeypatch):
    # Capture the reset link the service would email.
    sent = {}
    from app.di import _email_service
    from app.services.email_service import SendEmailResp

    def _fake_send(req):
        sent["body"] = req.body
        sent["to"] = req.to
        return SendEmailResp(sent=True)

    monkeypatch.setattr(_email_service, "send", _fake_send)

    with TestClient(app) as client:
        client.post("/auth/signup", json={"email": "pwreset@example.com", "password": "oldpw12345"})

        # unknown email -> still a generic 200 (no account enumeration)
        r0 = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
        assert r0.status_code == 200 and "reset link" in r0.json()["message"]

        r = client.post("/auth/forgot-password", json={"email": "pwreset@example.com"})
        assert r.status_code == 200
        assert sent["to"] == "pwreset@example.com"
        token = sent["body"].split("token=")[1].split()[0].strip()

        # reset to a new password
        rr = client.post("/auth/reset-password", json={"token": token, "new_password": "newpw67890"})
        assert rr.status_code == 200, rr.text

        # old password no longer works; new one does
        assert client.post("/auth/login", json={"email": "pwreset@example.com", "password": "oldpw12345"}).status_code == 401
        assert client.post("/auth/login", json={"email": "pwreset@example.com", "password": "newpw67890"}).status_code == 200

        # reset token is single-use
        assert client.post("/auth/reset-password", json={"token": token, "new_password": "x"}).status_code == 401


def test_email_verification_flow(monkeypatch):
    sent = {}
    from app.di import _email_service
    from app.services.email_service import SendEmailResp

    def _fake_send(req):
        sent["body"] = req.body
        return SendEmailResp(sent=True)

    monkeypatch.setattr(_email_service, "send", _fake_send)

    with TestClient(app) as client:
        tok = client.post(
            "/auth/signup", json={"email": "verify@example.com", "password": "pw123456"}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        # not verified yet
        assert client.get("/me", headers=h).json()["email_verified"] is False

        assert client.post("/auth/send-verification", headers=h).status_code == 200
        token = sent["body"].split("token=")[1].strip()

        assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
        assert client.get("/me", headers=h).json()["email_verified"] is True

        # single-use
        assert client.post("/auth/verify-email", json={"token": token}).status_code == 401


def test_onedrive_authorize_not_configured():
    with TestClient(app) as client:
        tok = client.post(
            "/auth/signup", json={"email": "od@example.com", "password": "pw123456"}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        # No MICROSOFT_OAUTH_CLIENT_ID in tests -> graceful 400 not_configured
        assert client.post("/me/connections/onedrive/authorize", headers=h).status_code == 400


def test_onedrive_authorize_url_when_configured(monkeypatch):
    from app.config import settings as cfg

    monkeypatch.setattr(cfg, "microsoft_oauth_client_id", "test-ms")
    monkeypatch.setattr(cfg, "microsoft_oauth_client_secret", "test-secret")
    with TestClient(app) as client:
        tok = client.post(
            "/auth/signup", json={"email": "od2@example.com", "password": "pw123456"}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        r = client.post("/me/connections/onedrive/authorize", headers=h)
        assert r.status_code == 200
        url = r.json()["authorize_url"]
        assert "login.microsoftonline.com" in url and "client_id=test-ms" in url and "state=" in url


def test_oauth_tokens_encrypted_at_rest(monkeypatch):
    """With a key configured, stored access/refresh tokens are ciphertext in the DB
    but decrypt transparently for use."""
    from app.config import settings as cfg
    from app.di import _connections_facade
    from app.dao.connection_dao import ConnectionDao
    from app.dtos.internal_dtos import CreateConnectionReq, GetConnectionReq, ListConnectionsReq
    from app.db import db as cust_db
    from image2prompt_shared.crypto import TokenCipher

    monkeypatch.setattr(cfg, "token_encryption_key", "unit-test-encryption-key")
    # rebuild the facade cipher to pick up the key
    _connections_facade.cipher = TokenCipher(cfg.token_encryption_key)

    with TestClient(app):
        session = cust_db.SessionLocal()
        try:
            dao = ConnectionDao()
            sealed = _connections_facade._seal_meta(
                {"real": True, "access_token": "AT-secret", "refresh_token": "RT-secret", "expires_at": 0}
            )
            created = dao.create(
                CreateConnectionReq(
                    db=session, customer_id="enc-cust", provider="google_drive",
                    display_name="Google Drive", account_email="x@example.com", meta=sealed,
                )
            )
            session.commit()
            # stored value is ciphertext
            assert TokenCipher.is_encrypted(created.connection.meta["access_token"])
            assert created.connection.meta["access_token"] != "AT-secret"
            # round-trips back to plaintext for use
            opened = _connections_facade._open_meta(created.connection.meta)
            assert opened["access_token"] == "AT-secret"
            assert opened["refresh_token"] == "RT-secret"
        finally:
            session.close()


def test_reencrypt_tokens_rotates_to_new_key(monkeypatch):
    """A connection sealed under key-A is re-sealed under key-B after rotation."""
    from app.config import settings as cfg
    from app.dao.connection_dao import ConnectionDao
    from app.db import db as cust_db
    from app.di import _connections_facade
    from app.dtos.internal_dtos import CreateConnectionReq, ReencryptTokensReq
    from app.models import Connection
    from image2prompt_shared.crypto import TokenCipher
    from sqlalchemy import select

    # seal under key-A
    monkeypatch.setattr(cfg, "token_encryption_key", "key-A")
    monkeypatch.setattr(cfg, "token_encryption_key_previous", "")
    _connections_facade.cipher = TokenCipher("key-A")

    with TestClient(app):
        session = cust_db.SessionLocal()
        try:
            sealed = _connections_facade._seal_meta(
                {"real": True, "access_token": "AT", "refresh_token": "RT", "expires_at": 0}
            )
            ConnectionDao().create(
                CreateConnectionReq(
                    db=session, customer_id="rot-cust", provider="google_drive",
                    display_name="Google Drive", account_email="x@example.com", meta=sealed,
                )
            )
            session.commit()

            # rotate to key-B (key-A as previous) and re-encrypt
            monkeypatch.setattr(cfg, "token_encryption_key", "key-B")
            monkeypatch.setattr(cfg, "token_encryption_key_previous", "key-A")
            _connections_facade.cipher = TokenCipher("key-B", previous_keys=["key-A"])

            resp = _connections_facade.reencrypt_tokens(ReencryptTokensReq(db=session))
            assert resp.count >= 1

            row = session.scalar(select(Connection).where(Connection.customer_id == "rot-cust"))
            # new ciphertext decrypts under key-B alone
            assert TokenCipher("key-B").decrypt(row.meta["access_token"]) == "AT"
            assert TokenCipher("key-A").decrypt(row.meta["access_token"]) == ""
        finally:
            session.close()


def test_google_authorize_not_configured():
    with TestClient(app) as client:
        tok = client.post(
            "/auth/signup", json={"email": "gd@example.com", "password": "pw123456"}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        # No GOOGLE_OAUTH_CLIENT_ID in tests -> graceful 400 not_configured
        r = client.post("/me/connections/google/authorize", headers=h)
        assert r.status_code == 400


def test_google_authorize_url_when_configured(monkeypatch):
    from app.config import settings as cfg

    monkeypatch.setattr(cfg, "google_oauth_client_id", "test-client")
    monkeypatch.setattr(cfg, "google_oauth_client_secret", "test-secret")
    with TestClient(app) as client:
        tok = client.post(
            "/auth/signup", json={"email": "gd2@example.com", "password": "pw123456"}
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        r = client.post("/me/connections/google/authorize", headers=h)
        assert r.status_code == 200
        url = r.json()["authorize_url"]
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert "client_id=test-client" in url and "state=" in url


def test_google_callback_bad_state_redirects_error():
    with TestClient(app) as client:
        r = client.get(
            "/me/connections/google/callback",
            params={"code": "x", "state": "not-a-valid-jwt"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "google=error" in r.headers["location"]
