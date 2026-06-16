"""Billing loop: KB subscription charges = plan price x stacks the customer uses.
Cross-service lookups (admin subscription, kb usage) are stubbed; Stripe is
unconfigured in tests so invoicing degrades gracefully."""

import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"
os.environ["SCHEDULER_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _signup(client, email="biller@example.com"):
    r = client.post("/auth/signup", json={"email": email, "password": "pw123456", "name": "B"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _stub_clients(monkeypatch):
    from app.di import _billing_client

    monkeypatch.setattr(
        _billing_client, "get_subscription",
        lambda cid: {
            "has_subscription": True, "plan_name": "Professional",
            "stacks": [
                {"stack": "pgvector", "monthly_cost": 0},
                {"stack": "pinecone", "monthly_cost": 49},
                {"stack": "weaviate", "monthly_cost": 49},
            ],
        },
    )
    monkeypatch.setattr(
        _billing_client, "get_kb_usage",
        lambda cid: [
            {"stack": "pgvector", "kb_count": 1, "doc_count": 5},
            {"stack": "pinecone", "kb_count": 2, "doc_count": 9},
            # weaviate is in the plan but unused -> not billed
        ],
    )


def test_billing_computes_subscription_charges(monkeypatch):
    _stub_clients(monkeypatch)
    with TestClient(app) as client:
        h = _signup(client)
        sub = client.get("/me/billing", headers=h).json()["subscription"]
        assert sub["has_subscription"] is True and sub["plan_name"] == "Professional"
        billed = {li["stack"]: li for li in sub["line_items"]}
        # only used stacks are billed; weaviate (unused) is absent
        assert set(billed) == {"pgvector", "pinecone"}
        assert billed["pinecone"]["monthly_cost"] == 49 and billed["pinecone"]["kb_count"] == 2
        # total = 0 (pgvector) + 49 (pinecone)
        assert sub["monthly_total"] == 49


def test_invoice_degrades_without_stripe(monkeypatch):
    _stub_clients(monkeypatch)
    with TestClient(app) as client:
        h = _signup(client, email="biller2@example.com")
        resp = client.post("/me/billing/invoice", headers=h).json()
        # no STRIPE_API_KEY in tests -> not configured, but the amount is still computed
        assert resp["configured"] is False
        assert resp["status"] == "stripe_not_configured"
        assert resp["amount"] == 49
        assert {li["stack"] for li in resp["line_items"]} == {"pgvector", "pinecone"}


def _stub_stripe(monkeypatch):
    """Make Stripe 'configured' and count invoice creations."""
    from app.di import _stripe_service
    from app.services.stripe_service import CreateInvoiceResp, EnsureCustomerResp

    monkeypatch.setattr(
        _stripe_service, "ensure_customer",
        lambda req: EnsureCustomerResp(configured=True, customer_id=req.existing_customer_id or "cus_x"),
    )
    counter = {"n": 0}

    def _fake_invoice(req):
        counter["n"] += 1
        return CreateInvoiceResp(configured=True, invoice_id=f"in_{counter['n']}", amount=49.0, status="open")

    monkeypatch.setattr(_stripe_service, "create_invoice", _fake_invoice)
    return counter


def test_invoice_is_idempotent_per_period(monkeypatch):
    _stub_clients(monkeypatch)
    counter = _stub_stripe(monkeypatch)
    with TestClient(app) as client:
        h = _signup(client, email="idem@example.com")
        r1 = client.post("/me/billing/invoice", headers=h).json()
        assert r1["already_billed"] is False and r1["invoice_id"] == "in_1" and r1["amount"] == 49.0
        # second call in the same month must NOT create another invoice
        r2 = client.post("/me/billing/invoice", headers=h).json()
        assert r2["already_billed"] is True and r2["invoice_id"] == "in_1"
        assert counter["n"] == 1  # billed exactly once despite two requests


def test_billing_sweep_bills_each_active_subscriber_once(monkeypatch):
    _stub_clients(monkeypatch)
    counter = _stub_stripe(monkeypatch)
    from app.di import _billing_client

    monkeypatch.setattr(
        _billing_client, "list_active_subscriptions",
        lambda: [{"customer_id": "sweep-1"}, {"customer_id": "sweep-2"}],
    )
    with TestClient(app):  # triggers bootstrap so billing_runs table exists
        from app.main import _run_billing_sweep

        _run_billing_sweep()
        _run_billing_sweep()  # a second sweep in the same month is idempotent
    assert counter["n"] == 2  # two subscribers billed once each, not four
