"""Smoke test for admin-service: seeded admin login + provider seed/toggle."""

import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"
os.environ["ADMIN_EMAIL"] = "admin@test.io"
os.environ["ADMIN_PASSWORD"] = "admin12345"
os.environ["SCHEDULER_ENABLED"] = "false"

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


def test_provider_config_encrypted_at_rest(monkeypatch):
    """With a key configured, provider config (API keys) is ciphertext in the DB
    but decrypts transparently on both admin and internal reads."""
    from app.config import settings as cfg
    from app.di import _providers_facade
    from app.db import db as admin_db
    from app.models import Provider
    from image2prompt_shared.crypto import TokenCipher
    from sqlalchemy import select

    monkeypatch.setattr(cfg, "token_encryption_key", "admin-unit-test-key")
    _providers_facade.cipher = TokenCipher(cfg.token_encryption_key)

    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}

        # set a secret on openai via PATCH
        oid = {p["key"]: p["id"] for p in client.get("/admin/providers", headers=h).json()}["openai"]
        r = client.patch(
            f"/admin/providers/{oid}",
            json={"enabled": True, "config": {"api_key": "sk-super-secret"}},
            headers=h,
        )
        assert r.status_code == 200
        # admin response masks the secret (raw value verified via DB + internal below)
        from app.masking import MASK

        assert r.json()["config"]["api_key"] == MASK

        # raw DB row is ciphertext (no plaintext secret on disk)
        session = admin_db.SessionLocal()
        try:
            row = session.scalar(select(Provider).where(Provider.id == oid))
            assert "_enc" in row.config
            assert TokenCipher.is_encrypted(row.config["_enc"])
            assert "sk-super-secret" not in json_dumps(row.config)
        finally:
            session.close()

        # internal endpoint (consumed by image-processing) returns plaintext
        internal = {p["key"]: p for p in client.get("/internal/providers", params={"enabled": "true"}).json()}
        assert internal["openai"]["config"] == {"api_key": "sk-super-secret"}


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj)


def test_admin_provider_config_is_masked_internal_is_not():
    """GET /admin/providers masks secret values; the internal endpoint returns
    them raw (image-processing needs the real keys)."""
    from app.masking import MASK

    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}
        oid = {p["key"]: p["id"] for p in client.get("/admin/providers", headers=h).json()}["cohere"]

        # set a secret + a non-secret field
        client.patch(
            f"/admin/providers/{oid}",
            json={"enabled": True, "config": {"api_key": "sk-raw-secret", "region": "us-east-1"}},
            headers=h,
        )

        # admin view: secret masked, non-secret visible
        admin_view = {p["key"]: p for p in client.get("/admin/providers", headers=h).json()}["cohere"]
        assert admin_view["config"]["api_key"] == MASK
        assert admin_view["config"]["region"] == "us-east-1"

        # internal view: real secret
        internal_view = {
            p["key"]: p for p in client.get("/internal/providers", params={"enabled": "true"}).json()
        }["cohere"]
        assert internal_view["config"]["api_key"] == "sk-raw-secret"


def test_update_with_masked_value_preserves_secret():
    """Re-submitting the masked sentinel must not overwrite the stored secret."""
    from app.masking import MASK

    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}
        oid = {p["key"]: p["id"] for p in client.get("/admin/providers", headers=h).json()}["mistral"]

        client.patch(f"/admin/providers/{oid}", json={"config": {"api_key": "sk-keep-me"}}, headers=h)
        # admin edits only the name, sending back the masked api_key unchanged
        client.patch(
            f"/admin/providers/{oid}",
            json={"name": "Mistral X", "config": {"api_key": MASK}},
            headers=h,
        )
        internal = {
            p["key"]: p for p in client.get("/internal/providers").json()
        }["mistral"]
        assert internal["config"]["api_key"] == "sk-keep-me"  # preserved, not wiped to MASK


def test_update_config_is_patch_merge():
    """A partial config update preserves unlisted keys; null deletes a key."""
    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}
        oid = {p["key"]: p["id"] for p in client.get("/admin/providers", headers=h).json()}["ollama"]

        client.patch(f"/admin/providers/{oid}", json={"config": {"host": "localhost", "api_key": "k1"}}, headers=h)
        # set only api_key -> host preserved
        client.patch(f"/admin/providers/{oid}", json={"config": {"api_key": "k2"}}, headers=h)
        cfg = {p["key"]: p for p in client.get("/internal/providers").json()}["ollama"]["config"]
        assert cfg["host"] == "localhost" and cfg["api_key"] == "k2"

        # null removes a key
        client.patch(f"/admin/providers/{oid}", json={"config": {"host": None}}, headers=h)
        cfg2 = {p["key"]: p for p in client.get("/internal/providers").json()}["ollama"]["config"]
        assert "host" not in cfg2 and cfg2["api_key"] == "k2"


def test_csp_violation_ingest_and_dashboard():
    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}

        # gateway-style internal ingest (no auth)
        for directive in ("img-src 'self'", "img-src 'self'", "script-src 'self'"):
            r = client.post(
                "/internal/csp-violations",
                json={
                    "document_uri": "https://app.example.com/",
                    "violated_directive": directive,
                    "blocked_uri": "https://evil.example.com/x.png",
                    "raw": {"k": "v"},
                },
            )
            assert r.status_code == 202

        # admin dashboard: identical reports are deduped into one row (count++),
        # so 3 reports -> 2 distinct rows but total volume 3.
        dash = client.get("/admin/csp-violations", headers=h).json()
        assert dash["total"] == 3
        assert len(dash["violations"]) == 2
        by_dir = {v["violated_directive"]: v for v in dash["violations"]}
        assert by_dir["img-src 'self'"]["count"] == 2
        assert by_dir["script-src 'self'"]["count"] == 1
        counts = {s["directive"]: s["count"] for s in dash["summary"]}
        assert counts["img-src 'self'"] == 2 and counts["script-src 'self'"] == 1

        # dashboard requires auth
        assert client.get("/admin/csp-violations").status_code == 401


def test_analytics_surfaces_csp_stats():
    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}
        for _ in range(2):
            client.post(
                "/internal/csp-violations",
                json={"violated_directive": "frame-ancestors 'none'", "blocked_uri": "x", "document_uri": "d"},
            )
        a = client.get("/admin/analytics", headers=h).json()
        assert "csp" in a
        assert a["csp"]["total"] >= 2
        assert a["csp"]["top_directive"] == "frame-ancestors 'none'"


def test_periodic_scheduler_runs_and_can_be_disabled():
    import asyncio

    from image2prompt_shared.scheduler import PeriodicScheduler

    async def run(enabled: bool) -> int:
        hits = {"n": 0}
        sched = PeriodicScheduler(enabled=enabled)
        sched.add_job(name="t", interval_seconds=0.05, func=lambda: hits.__setitem__("n", hits["n"] + 1), run_on_start=True)
        await sched.start()
        await asyncio.sleep(0.12)
        await sched.stop()
        return hits["n"]

    assert asyncio.run(run(True)) >= 1
    assert asyncio.run(run(False)) == 0


def test_csp_retention_prune_removes_old_rows():
    from datetime import timedelta

    from sqlalchemy import select

    from app.dao.csp_violation_dao import CspViolationDao
    from app.db import db as admin_db
    from app.models import CspViolation
    from image2prompt_shared.base import utcnow

    with TestClient(app):
        # ingest one violation, then backdate its last-seen well past retention
        session = admin_db.SessionLocal()
        try:
            CspViolationDao().create(
                type("R", (), {
                    "db": session, "violated_directive": "stale-dir", "blocked_uri": "b",
                    "document_uri": None, "source_file": None, "line_number": None,
                    "disposition": None, "user_agent": None, "raw": {},
                })()
            )
            session.commit()
            row = session.scalar(select(CspViolation).where(CspViolation.violated_directive == "stale-dir"))
            row.updated_at = utcnow() - timedelta(days=400)
            session.commit()

            removed = CspViolationDao().prune_older_than(session, utcnow() - timedelta(days=30))
            assert removed >= 1
            assert (
                session.scalar(select(CspViolation).where(CspViolation.violated_directive == "stale-dir"))
                is None
            )
        finally:
            session.close()


def test_token_cipher_rotation_decrypts_with_previous_key():
    from image2prompt_shared.crypto import TokenCipher

    old = TokenCipher("key-A")
    sealed = old.encrypt("super-secret")
    assert TokenCipher.is_encrypted(sealed)

    # new current key + old as previous -> still decrypts
    rotated = TokenCipher("key-B", previous_keys=["key-A"])
    assert rotated.decrypt(sealed) == "super-secret"

    # re-seal under the new key; a cipher with ONLY key-B can then read it,
    # and key-A alone can no longer decrypt the new ciphertext
    resealed = rotated.rotate(sealed)
    assert TokenCipher("key-B").decrypt(resealed) == "super-secret"
    assert TokenCipher("key-A").decrypt(resealed) == ""


def test_maintenance_prune_endpoint():
    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}
        r = client.post("/admin/maintenance/prune", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "revoked_tokens" in body and "csp_violations" in body


def test_maintenance_reencrypt_reseals_providers(monkeypatch):
    from app.config import settings as cfg
    from app.di import _providers_facade
    from app.db import db as admin_db
    from app.models import Provider
    from image2prompt_shared.crypto import TokenCipher
    from sqlalchemy import select

    # start under key-A, store a secret
    monkeypatch.setattr(cfg, "token_encryption_key", "key-A")
    monkeypatch.setattr(cfg, "token_encryption_key_previous", "")
    _providers_facade.cipher = TokenCipher("key-A")

    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}
        oid = {p["key"]: p["id"] for p in client.get("/admin/providers", headers=h).json()}["google"]
        client.patch(f"/admin/providers/{oid}", json={"config": {"api_key": "rotate-me"}}, headers=h)

        # rotate to key-B (key-A as previous), then re-encrypt
        monkeypatch.setattr(cfg, "token_encryption_key", "key-B")
        monkeypatch.setattr(cfg, "token_encryption_key_previous", "key-A")
        _providers_facade.cipher = TokenCipher("key-B", previous_keys=["key-A"])

        r = client.post("/admin/maintenance/reencrypt", headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["providers"] >= 1

        # stored ciphertext now decrypts under key-B alone
        session = admin_db.SessionLocal()
        try:
            row = session.scalar(select(Provider).where(Provider.id == oid))
            blob = row.config["_enc"]
            import json as _json

            assert _json.loads(TokenCipher("key-B").decrypt(blob))["api_key"] == "rotate-me"
        finally:
            session.close()

        # and the API still returns the (masked) config correctly
        from app.masking import MASK

        view = {p["key"]: p for p in client.get("/admin/providers", headers=h).json()}["google"]
        assert view["config"]["api_key"] == MASK


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


def test_admin_logout_revokes_refresh():
    with TestClient(app) as client:
        login = client.post(
            "/admin/auth/login", json={"email": "admin@test.io", "password": "admin12345"}
        ).json()
        assert client.post("/admin/auth/logout", json={"refresh_token": login["refresh_token"]}).status_code == 204
        assert client.post("/admin/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401


def test_viewer_role_is_read_only():
    from image2prompt_shared.security import create_access_token
    from app.config import settings as cfg

    viewer = create_access_token(
        subject="viewer-1", token_type="admin", email="viewer@test.io",
        secret=cfg.jwt_secret, algorithm=cfg.jwt_algorithm, extra={"role": "viewer"},
    )
    h = {"Authorization": f"Bearer {viewer}"}
    with TestClient(app) as client:
        # viewer can read providers
        providers = client.get("/admin/providers", headers=h)
        assert providers.status_code == 200
        pid = {p["key"]: p["id"] for p in providers.json()}["mock"]
        # but cannot mutate them
        assert client.patch(f"/admin/providers/{pid}", json={"enabled": True}, headers=h).status_code == 403


def test_admin_user_management():
    with TestClient(app) as client:
        token = _login(client)  # seeded superadmin
        h = {"Authorization": f"Bearer {token}"}

        # superadmin creates a viewer admin
        r = client.post(
            "/admin/users",
            json={"email": "viewer2@test.io", "password": "pw12345678", "role": "viewer"},
            headers=h,
        )
        assert r.status_code == 201, r.text
        new_id = r.json()["id"]
        assert r.json()["role"] == "viewer"

        # it shows in the listing
        emails = {a["email"] for a in client.get("/admin/users", headers=h).json()}
        assert "viewer2@test.io" in emails

        # the created viewer can log in but is read-only
        vt = client.post(
            "/admin/auth/login", json={"email": "viewer2@test.io", "password": "pw12345678"}
        ).json()["access_token"]
        vh = {"Authorization": f"Bearer {vt}"}
        assert client.get("/admin/users", headers=vh).status_code == 403  # not superadmin
        prov = client.get("/admin/providers", headers=vh)
        pid = {p["key"]: p["id"] for p in prov.json()}["mock"]
        assert client.patch(f"/admin/providers/{pid}", json={"enabled": True}, headers=vh).status_code == 403

        # delete the viewer
        assert client.delete(f"/admin/users/{new_id}", headers=h).status_code == 204


def test_edit_admin_role_and_self_guard():
    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}
        # create a viewer, then promote to admin
        new_id = client.post(
            "/admin/users",
            json={"email": "promote@test.io", "password": "pw12345678", "role": "viewer"},
            headers=h,
        ).json()["id"]
        upd = client.patch(f"/admin/users/{new_id}", json={"role": "admin"}, headers=h)
        assert upd.status_code == 200 and upd.json()["role"] == "admin"
        # promoted admin can now mutate providers
        at = client.post(
            "/admin/auth/login", json={"email": "promote@test.io", "password": "pw12345678"}
        ).json()["access_token"]
        ah = {"Authorization": f"Bearer {at}"}
        pid = {p["key"]: p["id"] for p in client.get("/admin/providers", headers=ah).json()}["mock"]
        assert client.patch(f"/admin/providers/{pid}", json={"enabled": True}, headers=ah).status_code == 200
        # superadmin cannot change own role
        me = {a["email"]: a["id"] for a in client.get("/admin/users", headers=h).json()}["admin@test.io"]
        assert client.patch(f"/admin/users/{me}", json={"role": "viewer"}, headers=h).status_code == 400
        # password reset works
        assert client.patch(f"/admin/users/{new_id}", json={"password": "newpw99999"}, headers=h).status_code == 200
        assert client.post(
            "/admin/auth/login", json={"email": "promote@test.io", "password": "newpw99999"}
        ).status_code == 200
