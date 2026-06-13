"""Smoke test for ai-adapters: the mock provider works offline; stubs error cleanly."""

import base64

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
IMG_B64 = base64.b64encode(b"fake-image-bytes").decode()


def test_mock_provider_success():
    r = client.post(
        "/invoke",
        json={
            "provider_key": "mock",
            "request_id": "req-1",
            "instruction": "describe",
            "image_base64": IMG_B64,
            "media_type": "image/png",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert body["output_text"]


def test_stub_provider_not_implemented():
    r = client.post(
        "/invoke",
        json={"provider_key": "openai", "request_id": "req-2", "image_base64": IMG_B64},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["error"]["type"] == "not_implemented"


def test_strands_is_a_real_provider():
    # Strands is implemented (not a stub) and advertised as such.
    providers = {p["key"]: p for p in client.get("/providers").json()}
    assert "strands" in providers
    assert providers["strands"]["implemented"] is True


def test_strands_without_sdk_degrades_gracefully():
    # The Strands SDK isn't installed in the test env; the real controller tries
    # to import it and the service returns an error envelope (never 500/raises).
    r = client.post(
        "/invoke",
        json={"provider_key": "strands", "request_id": "req-s", "image_base64": IMG_B64},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["error"] is not None


def test_framework_providers_are_real():
    providers = {p["key"]: p for p in client.get("/providers").json()}
    for key in ("strands", "langgraph", "crewai", "llamaindex"):
        assert providers[key]["implemented"] is True, key


def test_framework_providers_degrade_without_sdk():
    # Framework SDKs aren't installed in the test env; invoking returns an error
    # envelope (HTTP 200, status=error) rather than raising.
    for key in ("langgraph", "crewai", "llamaindex"):
        r = client.post(
            "/invoke", json={"provider_key": key, "request_id": "r", "image_base64": IMG_B64}
        )
        assert r.status_code == 200, key
        assert r.json()["status"] == "error", key


def test_unknown_provider_404():
    r = client.post(
        "/invoke",
        json={"provider_key": "does-not-exist", "request_id": "req-3", "image_base64": IMG_B64},
    )
    assert r.status_code == 404
