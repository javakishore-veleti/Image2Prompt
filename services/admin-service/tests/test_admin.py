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


def test_token_cipher_key_versioning():
    from image2prompt_shared.crypto import TokenCipher

    c = TokenCipher("vkey")
    sealed = c.encrypt("s")
    assert sealed.startswith("enc:v2:")
    assert TokenCipher.key_id(sealed) == TokenCipher.fingerprint("vkey")
    assert c.is_current(sealed) is True

    # a cipher whose current key differs sees it as not-current, but still decrypts
    c2 = TokenCipher("vkey2", previous_keys=["vkey"])
    assert c2.is_current(sealed) is False
    assert c2.decrypt(sealed) == "s"

    # legacy v1 values have no key id and are never "current"
    assert TokenCipher.key_id("enc:v1:abc") is None


def test_rotation_status_reports_stale(monkeypatch):
    from app.config import settings as cfg
    from app.di import _providers_facade
    from image2prompt_shared.crypto import TokenCipher

    # seal a provider under the old key
    monkeypatch.setattr(cfg, "token_encryption_key", "rot-old")
    monkeypatch.setattr(cfg, "token_encryption_key_previous", "")
    monkeypatch.setattr(_providers_facade, "cipher", TokenCipher("rot-old"))
    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}
        oid = {p["key"]: p["id"] for p in client.get("/admin/providers", headers=h).json()}["anthropic"]
        client.patch(f"/admin/providers/{oid}", json={"config": {"api_key": "x"}}, headers=h)

        # rotate the current key -> the anthropic config is now stale
        monkeypatch.setattr(cfg, "token_encryption_key", "rot-new")
        monkeypatch.setattr(cfg, "token_encryption_key_previous", "rot-old")
        monkeypatch.setattr(_providers_facade, "cipher", TokenCipher("rot-new", previous_keys=["rot-old"]))

        rs = client.get("/admin/maintenance/rotation-status", headers=h).json()
        assert rs["key_id"] == TokenCipher.fingerprint("rot-new")
        assert rs["providers"]["stale"] >= 1
        assert rs["providers"]["total"] >= rs["providers"]["stale"]


def test_audit_log_records_provider_and_maintenance_actions():
    with TestClient(app) as client:
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}

        # a credential change + a prune should both be audited
        oid = {p["key"]: p["id"] for p in client.get("/admin/providers", headers=h).json()}["llamaindex"]
        client.patch(f"/admin/providers/{oid}", json={"config": {"api_key": "secret-val"}}, headers=h)
        client.post("/admin/maintenance/prune", headers=h)

        entries = client.get("/admin/audit-log", headers=h).json()
        actions = [e["action"] for e in entries]
        assert "provider.update" in actions
        assert "maintenance.prune" in actions

        upd = next(e for e in entries if e["action"] == "provider.update")
        assert upd["actor_email"] == "admin@test.io"
        assert upd["target"] == "llamaindex"
        # detail records the key NAME only, never the secret value
        assert upd["detail"]["config_set"] == ["api_key"]
        import json as _json

        assert "secret-val" not in _json.dumps(entries)

        # audit log requires auth
        assert client.get("/admin/audit-log").status_code == 401


def test_audit_log_filter_and_export():
    import json as _json

    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}
        client.post("/admin/maintenance/prune", headers=h)

        # filter by action + total-count header
        r = client.get("/admin/audit-log", params={"action": "maintenance.prune"}, headers=h)
        rows = r.json()
        assert rows and all(rr["action"] == "maintenance.prune" for rr in rows)
        assert int(r.headers["X-Total-Count"]) >= len(rows)

        # filter by actor substring
        rows2 = client.get("/admin/audit-log", params={"actor": "admin@test"}, headers=h).json()
        assert rows2 and all("admin@test" in (r["actor_email"] or "") for r in rows2)

        # NDJSON export (filtered)
        exp = client.get("/admin/audit-log/export", params={"action": "maintenance.prune"}, headers=h)
        assert exp.status_code == 200
        assert exp.headers["content-type"].startswith("application/x-ndjson")
        assert "attachment" in exp.headers.get("content-disposition", "")
        lines = [_json.loads(ln) for ln in exp.text.splitlines() if ln]
        assert lines and all(ln["action"] == "maintenance.prune" for ln in lines)


def test_audit_log_covers_auth_and_admin_user_actions():
    with TestClient(app) as client:
        # a failed login is audited (actor = attempted email), then a success
        client.post("/admin/auth/login", json={"email": "admin@test.io", "password": "nope"})
        token = _login(client)
        h = {"Authorization": f"Bearer {token}"}

        # superadmin creates + updates + deletes an admin user
        new = client.post(
            "/admin/users", json={"email": "auditee@image2prompt.io", "password": "pw123456", "role": "viewer"}, headers=h
        ).json()
        client.patch(f"/admin/users/{new['id']}", json={"role": "admin"}, headers=h)
        client.delete(f"/admin/users/{new['id']}", headers=h)

        actions = [e["action"] for e in client.get("/admin/audit-log", headers=h).json()]
        for expected in (
            "admin.login.failure",
            "admin.login.success",
            "admin_user.create",
            "admin_user.update",
            "admin_user.delete",
        ):
            assert expected in actions, expected


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


def test_admin_cross_customer_activity(monkeypatch):
    from app.di import _customers_facade
    from app.dtos.internal_dtos import CustomerActivityResp

    async def _fake_activity(req):
        assert req.customer_id == "cust-xyz"
        return CustomerActivityResp(
            entries=[{"id": "1", "action": "customer.login.success", "target": None, "detail": {}}]
        )

    monkeypatch.setattr(_customers_facade.directory_service, "get_activity", _fake_activity)

    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}
        r = client.get("/admin/customers/cust-xyz/activity", headers=h)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body and body[0]["action"] == "customer.login.success"

        # requires admin auth
        assert client.get("/admin/customers/cust-xyz/activity").status_code == 401


def test_admin_account_lockout(monkeypatch):
    from app.config import settings as cfg

    monkeypatch.setattr(cfg, "login_lockout_threshold", 3)
    with TestClient(app) as client:
        # use a dedicated admin so the seeded login account isn't locked for other tests
        h = {"Authorization": f"Bearer {_login(client)}"}
        client.post(
            "/admin/users",
            json={"email": "locktarget@image2prompt.io", "password": "pw123456", "role": "viewer"},
            headers=h,
        )
        for _ in range(3):
            r = client.post(
                "/admin/auth/login", json={"email": "locktarget@image2prompt.io", "password": "wrong"}
            )
            assert r.status_code == 401
        # locked: correct password now rejected with 423
        r = client.post(
            "/admin/auth/login", json={"email": "locktarget@image2prompt.io", "password": "pw123456"}
        )
        assert r.status_code == 423, r.text


def test_superadmin_unlock_clears_admin_lockout(monkeypatch):
    from app.config import settings as cfg

    monkeypatch.setattr(cfg, "login_lockout_threshold", 3)
    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}
        new = client.post(
            "/admin/users",
            json={"email": "unlockadmin@image2prompt.io", "password": "pw123456", "role": "viewer"},
            headers=h,
        ).json()
        for _ in range(3):
            assert client.post(
                "/admin/auth/login", json={"email": "unlockadmin@image2prompt.io", "password": "x"}
            ).status_code == 401
        assert client.post(
            "/admin/auth/login", json={"email": "unlockadmin@image2prompt.io", "password": "pw123456"}
        ).status_code == 423
        # superadmin releases the lock
        assert client.post(f"/admin/users/{new['id']}/unlock", headers=h).status_code == 200
        assert client.post(
            "/admin/auth/login", json={"email": "unlockadmin@image2prompt.io", "password": "pw123456"}
        ).status_code == 200


def test_subscriptions_crud_assign_and_report():
    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}

        # tech-stack catalog
        stacks = client.get("/admin/subscriptions/tech-stacks", headers=h).json()
        assert "pgvector" in stacks and "bedrock" in stacks

        # reject an unknown stack
        bad = client.post(
            "/admin/subscriptions",
            json={"name": "Bad", "stacks": [{"stack": "nope", "monthly_cost": 1}]},
            headers=h,
        )
        assert bad.status_code == 400

        # create a plan with per-stack pricing
        plan = client.post(
            "/admin/subscriptions",
            json={
                "name": "Pro",
                "description": "pgvector + chroma",
                "stacks": [
                    {"stack": "pgvector", "monthly_cost": 10},
                    {"stack": "chroma", "monthly_cost": 0},
                ],
            },
            headers=h,
        ).json()
        pid = plan["id"]
        assert {s["stack"] for s in plan["stacks"]} == {"pgvector", "chroma"}

        # duplicate name rejected
        assert client.post("/admin/subscriptions", json={"name": "Pro"}, headers=h).status_code == 409

        # list + search
        assert any(p["id"] == pid for p in client.get("/admin/subscriptions", headers=h).json())
        assert client.get("/admin/subscriptions", params={"search": "Pro"}, headers=h).json()

        # assign two customers, then report by plan with search
        client.post(f"/admin/subscriptions/{pid}/customers",
                    json={"customer_id": "c1", "customer_email": "alice@acme.io"}, headers=h)
        client.post(f"/admin/subscriptions/{pid}/customers",
                    json={"customer_id": "c2", "customer_email": "bob@acme.io"}, headers=h)
        report = client.get(f"/admin/subscriptions/{pid}/customers", headers=h).json()
        assert {r["customer_id"] for r in report} == {"c1", "c2"}
        filtered = client.get(f"/admin/subscriptions/{pid}/customers", params={"search": "alice"}, headers=h).json()
        assert [r["customer_id"] for r in filtered] == ["c1"]

        # internal gating view (consumed by kb-service)
        view = client.get("/internal/subscriptions/customer/c1").json()
        assert view["has_subscription"] is True and view["plan_name"] == "Pro"
        assert {s["stack"] for s in view["stacks"]} == {"pgvector", "chroma"}
        # a customer with no plan
        none_view = client.get("/internal/subscriptions/customer/nobody").json()
        assert none_view["has_subscription"] is False

        # CRUD requires auth
        assert client.get("/admin/subscriptions").status_code == 401


def test_plan_quotas_persist_and_surface_internally():
    """Per-plan quotas (max_kbs / max_docs_per_kb) round-trip and reach kb-service
    via the internal subscription view."""
    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}
        plan = client.post(
            "/admin/subscriptions",
            json={
                "name": "Capped",
                "stacks": [{"stack": "pgvector", "monthly_cost": 0}],
                "max_kbs": 3, "max_docs_per_kb": 100,
            },
            headers=h,
        ).json()
        assert plan["max_kbs"] == 3 and plan["max_docs_per_kb"] == 100
        # PATCH to unlimited (explicit null) clears the cap
        upd = client.patch(f"/admin/subscriptions/{plan['id']}", json={"max_kbs": None}, headers=h).json()
        assert upd["max_kbs"] is None and upd["max_docs_per_kb"] == 100

        client.post(f"/admin/subscriptions/{plan['id']}/customers",
                    json={"customer_id": "qc1", "customer_email": "q@acme.io"}, headers=h)
        view = client.get("/internal/subscriptions/customer/qc1").json()
        assert view["max_kbs"] is None and view["max_docs_per_kb"] == 100


def test_revenue_rollup():
    """Contracted MRR = active subscribers × plan list price (sum of stack costs)."""
    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}
        plan = client.post(
            "/admin/subscriptions",
            json={"name": "RevPlan", "stacks": [
                {"stack": "pgvector", "monthly_cost": 10},
                {"stack": "pinecone", "monthly_cost": 20},
            ]},
            headers=h,
        ).json()
        for cid in ("rev1", "rev2"):
            client.post(f"/admin/subscriptions/{plan['id']}/customers",
                        json={"customer_id": cid, "customer_email": f"{cid}@acme.io"}, headers=h)

        rollup = client.get("/admin/subscriptions/revenue", headers=h).json()
        row = next(p for p in rollup["plans"] if p["plan_name"] == "RevPlan")
        assert row["plan_price"] == 30 and row["customers"] == 2 and row["mrr"] == 60
        assert rollup["total_mrr"] >= 60
        # requires auth
        assert client.get("/admin/subscriptions/revenue").status_code == 401


def test_internal_active_subscriptions_list():
    """The scheduled billing sweep in customer-service reads active subscriptions
    (with plan + pricing) from this internal endpoint."""
    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}
        plan = client.post(
            "/admin/subscriptions",
            json={"name": "Sweep", "stacks": [{"stack": "pgvector", "monthly_cost": 12}]},
            headers=h,
        ).json()
        client.post(f"/admin/subscriptions/{plan['id']}/customers",
                    json={"customer_id": "sc1", "customer_email": "sc1@acme.io"}, headers=h)
        client.post(f"/admin/subscriptions/{plan['id']}/customers",
                    json={"customer_id": "sc2", "customer_email": "sc2@acme.io"}, headers=h)

        items = client.get("/internal/subscriptions/active").json()["items"]
        mine = {i["customer_id"]: i for i in items if i["plan_name"] == "Sweep"}
        assert set(mine) == {"sc1", "sc2"}
        assert mine["sc1"]["stacks"] == [{"stack": "pgvector", "monthly_cost": 12}]


def test_default_subscription_plans_seeded():
    """A fresh deploy ships starter plans so customers can be assigned out of the box."""
    with TestClient(app) as client:
        h = {"Authorization": f"Bearer {_login(client)}"}
        plans = {p["name"]: p for p in client.get("/admin/subscriptions", headers=h).json()}
        assert {"Starter", "Professional", "Enterprise"} <= set(plans)
        # Enterprise includes every tech stack; Starter is the free local pair.
        assert {s["stack"] for s in plans["Starter"]["stacks"]} == {"pgvector", "chroma"}
        assert "bedrock" in {s["stack"] for s in plans["Enterprise"]["stacks"]}
        # pgvector is priced at 0 (locally runnable) in the seeded plans.
        pg = next(s for s in plans["Professional"]["stacks"] if s["stack"] == "pgvector")
        assert pg["monthly_cost"] == 0


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
