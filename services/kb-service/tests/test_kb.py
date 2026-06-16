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


def test_registry_maps_every_stack():
    """Every catalog stack resolves to its dedicated store class; unknown -> base."""
    from app.services.vectorstores import VectorStore, build_vector_store
    from app.services.vectorstores.bedrock import BedrockKbStore
    from app.services.vectorstores.chroma import ChromaVectorStore
    from app.services.vectorstores.mongodb import MongoVectorStore
    from app.services.vectorstores.neo4j_store import Neo4jVectorStore
    from app.services.vectorstores.opensearch import OpenSearchStore
    from app.services.vectorstores.pinecone_store import PineconeStore
    from app.services.vectorstores.sql import SqlVectorStore
    from app.services.vectorstores.weaviate_store import WeaviateStore

    expected = {
        "pgvector": SqlVectorStore,
        "chroma": ChromaVectorStore,
        "bedrock": BedrockKbStore,
        "opensearch": OpenSearchStore,
        "mongodb": MongoVectorStore,
        "neo4j": Neo4jVectorStore,
        "pinecone": PineconeStore,
        "weaviate": WeaviateStore,
    }
    for stack, cls in expected.items():
        assert isinstance(build_vector_store(stack), cls)
    # unknown stack -> in-process base store
    fallback = build_vector_store("does-not-exist")
    assert type(fallback) is VectorStore and fallback.ready() is False


def test_unconfigured_cloud_store_degrades(monkeypatch):
    """A cloud stack with no credentials is not ready, but still ingests + queries
    end-to-end via the in-process fallback (never raises)."""
    async def _resolve(customer_id, ids):
        return [g for g in _FAKE_GENS if g["id"] in ids]

    monkeypatch.setattr(_generation_client, "resolve", _resolve)

    from app.services.vectorstores import build_vector_store

    store = build_vector_store("pinecone")
    assert store.ready() is False  # no PINECONE_API_KEY in tests

    with TestClient(app) as client:
        h = _auth("cloud-cust")
        g = client.post("/groups", json={"project_id": "pc", "name": "G"}, headers=h).json()
        kb = client.post(
            "/kbs",
            json={"group_id": g["id"], "project_id": "pc", "name": "Cloud KB", "tech_stack": "pinecone"},
            headers=h,
        ).json()
        assert kb["tech_stack"] == "pinecone" and kb["backend_ready"] is False
        ing = client.post(f"/kbs/{kb['id']}/ingest", json={"generation_ids": ["g1", "g2"]}, headers=h).json()
        assert ing["ingested"] == 2
        res = client.post(
            f"/kbs/{kb['id']}/query", json={"query": "sunset over mountains", "top_k": 2}, headers=h
        ).json()
        assert res["results"] and res["results"][0]["generation_id"] == "g1"


def test_async_ingest_job(monkeypatch):
    """Async ingest queues a background job; polling shows it completed and the
    documents landed (TestClient runs background tasks before returning)."""
    async def _resolve(customer_id, ids):
        return [g for g in _FAKE_GENS if g["id"] in ids]

    monkeypatch.setattr(_generation_client, "resolve", _resolve)

    with TestClient(app) as client:
        h = _auth("async-cust")
        g = client.post("/groups", json={"project_id": "pa", "name": "G"}, headers=h).json()
        kb = client.post(
            "/kbs", json={"group_id": g["id"], "project_id": "pa", "name": "K", "tech_stack": "pgvector"}, headers=h
        ).json()
        r = client.post(f"/kbs/{kb['id']}/ingest-async", json={"generation_ids": ["g1", "g2"]}, headers=h)
        assert r.status_code == 202
        job = r.json()
        assert job["requested"] == 2 and job["status"] in ("pending", "running", "done")

        status = client.get(f"/kbs/{kb['id']}/ingest-jobs/{job['id']}", headers=h).json()
        assert status["status"] == "done" and status["ingested"] == 2 and status["skipped"] == 0
        assert len(client.get(f"/kbs/{kb['id']}/documents", headers=h).json()) == 2
        # another customer can't read the job
        assert client.get(f"/kbs/{kb['id']}/ingest-jobs/{job['id']}", headers=_auth("nosy")).status_code == 404


def test_delete_kb_removes_docs_vectors_and_usage(monkeypatch):
    """Deleting a KB purges its documents + vectors and drops it from usage."""
    async def _resolve(customer_id, ids):
        return [g for g in _FAKE_GENS if g["id"] in ids]

    monkeypatch.setattr(_generation_client, "resolve", _resolve)

    with TestClient(app) as client:
        h = _auth("del-cust")
        g = client.post("/groups", json={"project_id": "pd", "name": "G"}, headers=h).json()
        kb = client.post(
            "/kbs", json={"group_id": g["id"], "project_id": "pd", "name": "K", "tech_stack": "pgvector"}, headers=h
        ).json()
        client.post(f"/kbs/{kb['id']}/ingest", json={"generation_ids": ["g1", "g2"]}, headers=h)
        assert len(client.get(f"/kbs/{kb['id']}/documents", headers=h).json()) == 2

        # delete the KB
        d = client.delete(f"/kbs/{kb['id']}", headers=h).json()
        assert d == {"deleted_kbs": 1, "deleted_docs": 2}
        # KB is gone, and no longer counted toward usage/billing
        assert client.get(f"/kbs/{kb['id']}", headers=h).status_code == 404
        assert client.get("/internal/usage/customer/del-cust").json()["stacks"] == []
        # double-delete is a clean 404
        assert client.delete(f"/kbs/{kb['id']}", headers=h).status_code == 404


def test_delete_group_cascades_to_kbs(monkeypatch):
    async def _resolve(customer_id, ids):
        return [g for g in _FAKE_GENS if g["id"] in ids]

    monkeypatch.setattr(_generation_client, "resolve", _resolve)

    with TestClient(app) as client:
        h = _auth("delgrp-cust")
        g = client.post("/groups", json={"project_id": "pg2", "name": "G"}, headers=h).json()
        k1 = client.post("/kbs", json={"group_id": g["id"], "project_id": "pg2", "name": "A", "tech_stack": "pgvector"}, headers=h).json()
        k2 = client.post("/kbs", json={"group_id": g["id"], "project_id": "pg2", "name": "B", "tech_stack": "chroma"}, headers=h).json()
        client.post(f"/kbs/{k1['id']}/ingest", json={"generation_ids": ["g1"]}, headers=h)

        d = client.delete(f"/groups/{g['id']}", headers=h).json()
        assert d["deleted_kbs"] == 2 and d["deleted_docs"] == 1
        assert client.get(f"/kbs/{k1['id']}", headers=h).status_code == 404
        assert client.get(f"/kbs/{k2['id']}", headers=h).status_code == 404
        # another customer can't delete someone's group
        assert client.delete(f"/groups/{g['id']}", headers=_auth("intruder")).status_code == 404


def test_internal_usage_reports_per_stack_counts(monkeypatch):
    """The /internal usage endpoint (consumed by customer-service billing) returns
    one entry per tech stack with KB and doc counts for the customer."""
    async def _resolve(customer_id, ids):
        return [g for g in _FAKE_GENS if g["id"] in ids]

    monkeypatch.setattr(_generation_client, "resolve", _resolve)

    with TestClient(app) as client:
        h = _auth("usage-cust")
        g = client.post("/groups", json={"project_id": "pu", "name": "G"}, headers=h).json()
        # one pgvector KB with two docs, one chroma KB with one doc
        pg = client.post(
            "/kbs", json={"group_id": g["id"], "project_id": "pu", "name": "PG", "tech_stack": "pgvector"}, headers=h
        ).json()
        ch = client.post(
            "/kbs", json={"group_id": g["id"], "project_id": "pu", "name": "CH", "tech_stack": "chroma"}, headers=h
        ).json()
        client.post(f"/kbs/{pg['id']}/ingest", json={"generation_ids": ["g1", "g2"]}, headers=h)
        client.post(f"/kbs/{ch['id']}/ingest", json={"generation_ids": ["g1"]}, headers=h)

        usage = client.get("/internal/usage/customer/usage-cust").json()
        by_stack = {s["stack"]: s for s in usage["stacks"]}
        assert by_stack["pgvector"] == {"stack": "pgvector", "kb_count": 1, "doc_count": 2}
        assert by_stack["chroma"] == {"stack": "chroma", "kb_count": 1, "doc_count": 1}
        # a customer with no KBs reports nothing
        assert client.get("/internal/usage/customer/nobody").json()["stacks"] == []


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


def test_plan_quota_caps_kb_count(monkeypatch):
    monkeypatch.setattr(cfg, "kb_require_subscription", True)
    from app.di import _subscription_client

    async def _sub(_cid):
        return {"has_subscription": True, "plan_name": "Starter",
                "stacks": [{"stack": "pgvector", "monthly_cost": 0}], "max_kbs": 1}

    monkeypatch.setattr(_subscription_client, "get_customer_subscription", _sub)

    with TestClient(app) as client:
        h = _auth("cap-kbs")
        g = client.post("/groups", json={"project_id": "pq", "name": "G"}, headers=h).json()
        body = {"group_id": g["id"], "project_id": "pq", "name": "k", "tech_stack": "pgvector"}
        assert client.post("/kbs", json={**body, "name": "k1"}, headers=h).status_code == 201
        # second KB exceeds the plan's max_kbs=1 -> 403
        over = client.post("/kbs", json={**body, "name": "k2"}, headers=h)
        assert over.status_code == 403 and "limit" in over.json()["detail"].lower()


def test_plan_quota_caps_docs_per_kb(monkeypatch):
    monkeypatch.setattr(cfg, "kb_require_subscription", True)
    from app.di import _subscription_client

    async def _sub(_cid):
        return {"has_subscription": True, "plan_name": "Starter",
                "stacks": [{"stack": "pgvector", "monthly_cost": 0}], "max_docs_per_kb": 1}

    async def _resolve(customer_id, ids):
        return [g for g in _FAKE_GENS if g["id"] in ids]

    monkeypatch.setattr(_subscription_client, "get_customer_subscription", _sub)
    monkeypatch.setattr(_generation_client, "resolve", _resolve)

    with TestClient(app) as client:
        h = _auth("cap-docs")
        g = client.post("/groups", json={"project_id": "pqd", "name": "G"}, headers=h).json()
        kb = client.post(
            "/kbs", json={"group_id": g["id"], "project_id": "pqd", "name": "k", "tech_stack": "pgvector"}, headers=h
        ).json()
        # plan caps docs at 1: ingest of 2 generations ingests 1, skips the rest
        ing = client.post(f"/kbs/{kb['id']}/ingest", json={"generation_ids": ["g1", "g2"]}, headers=h).json()
        assert ing["ingested"] == 1 and ing["skipped"] == 1 and ing["doc_count"] == 1


def test_my_subscription_scopes_allowed_stacks(monkeypatch):
    monkeypatch.setattr(cfg, "kb_require_subscription", True)
    from app.di import _subscription_client

    async def _sub(_cid):
        return {"has_subscription": True, "plan_name": "Professional", "max_kbs": 25,
                "stacks": [{"stack": "pgvector", "monthly_cost": 0}, {"stack": "pinecone", "monthly_cost": 49}]}

    monkeypatch.setattr(_subscription_client, "get_customer_subscription", _sub)

    with TestClient(app) as client:
        h = _auth("mysub")
        sub = client.get("/my-subscription", headers=h).json()
        assert sub["has_subscription"] is True and sub["plan_name"] == "Professional"
        assert set(sub["stacks"]) == {"pgvector", "pinecone"} and sub["max_kbs"] == 25
