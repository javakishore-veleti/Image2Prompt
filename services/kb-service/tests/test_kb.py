"""kb-service tests (SQLite-backed). The pgvector stack maps to the SQL-backed
vector store, so ingest+query run for real. Cross-service calls are stubbed."""

import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"
os.environ["KB_REQUIRE_SUBSCRIPTION"] = "false"  # admin-service not running in tests

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings as cfg  # noqa: E402
from app.di import _generation_client  # noqa: E402
from app.main import app  # noqa: E402
from image2prompt_shared.security import create_access_token  # noqa: E402


def _auth(customer_id="cust-1"):
    tok = create_access_token(
        subject=customer_id, token_type="customer", email=f"{customer_id}@x.io",
        secret=cfg.jwt_secret, algorithm=cfg.jwt_algorithm, expire_minutes=60,
    )
    return {"Authorization": f"Bearer {tok}"}


_FAKE_GENS = [
    {"id": "g1", "instruction": "describe", "project_id": "p1", "file_ref_id": "f1",
     "prompts": [{"provider_key": "mock", "output_text": "a golden sunset over snowy mountains, dramatic sky"}]},
    {"id": "g2", "instruction": "describe", "project_id": "p1", "file_ref_id": "f2",
     "prompts": [{"provider_key": "mock", "output_text": "a neon city street at night in the rain"}]},
]


def test_kb_end_to_end(monkeypatch):
    async def _resolve(customer_id, ids):
        return [g for g in _FAKE_GENS if g["id"] in ids]

    monkeypatch.setattr(_generation_client, "resolve", _resolve)

    with TestClient(app) as client:
        h = _auth()
        # tech-stack catalog
        assert "pgvector" in client.get("/tech-stacks", headers=h).json()

        # group + KB (pgvector -> real SQL-backed store)
        g = client.post("/groups", json={"project_id": "p1", "name": "Brand assets"}, headers=h).json()
        kb = client.post(
            "/kbs",
            json={"group_id": g["id"], "project_id": "p1", "name": "Sunsets KB", "tech_stack": "pgvector"},
            headers=h,
        ).json()
        assert kb["tech_stack"] == "pgvector" and kb["backend_ready"] is True

        # ingest two generations
        ing = client.post(f"/kbs/{kb['id']}/ingest", json={"generation_ids": ["g1", "g2"]}, headers=h).json()
        assert ing["ingested"] == 2 and ing["doc_count"] == 2
        # re-ingest is deduped
        again = client.post(f"/kbs/{kb['id']}/ingest", json={"generation_ids": ["g1"]}, headers=h).json()
        assert again["ingested"] == 0 and again["skipped"] == 1

        # documents listed
        assert len(client.get(f"/kbs/{kb['id']}/documents", headers=h).json()) == 2

        # semantic query ranks the sunset doc first
        res = client.post(f"/kbs/{kb['id']}/query", json={"query": "sunset over mountains", "top_k": 2}, headers=h).json()
        assert res["results"] and res["results"][0]["generation_id"] == "g1"

        # another customer can't see this KB
        assert client.get(f"/kbs/{kb['id']}", headers=_auth("intruder")).status_code == 404
        # auth required
        assert client.get("/kbs").status_code == 401


def test_subscription_gating(monkeypatch):
    monkeypatch.setattr(cfg, "kb_require_subscription", True)
    from app.di import _subscription_client

    async def _sub(_cid):
        return {"has_subscription": True, "stacks": [{"stack": "pgvector", "monthly_cost": 10}]}

    monkeypatch.setattr(_subscription_client, "get_customer_subscription", _sub)

    with TestClient(app) as client:
        h = _auth("gated")
        g = client.post("/groups", json={"project_id": "p9", "name": "G"}, headers=h).json()
        # allowed stack
        ok = client.post("/kbs", json={"group_id": g["id"], "project_id": "p9", "name": "ok", "tech_stack": "pgvector"}, headers=h)
        assert ok.status_code == 201
        # disallowed stack -> 403
        no = client.post("/kbs", json={"group_id": g["id"], "project_id": "p9", "name": "no", "tech_stack": "pinecone"}, headers=h)
        assert no.status_code == 403
