"""Smoke test for ai-adapters: the mock provider works offline; every other
provider is implemented and degrades to an error envelope without SDK/creds."""

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


ALL_REAL = (
    "bedrock", "strands", "langgraph", "crewai", "llamaindex",
    "google", "openai", "anthropic", "microsoft",
)


def test_all_providers_are_implemented():
    # No stubs remain — every registered provider reports implemented=True.
    providers = {p["key"]: p for p in client.get("/providers").json()}
    for key in (*ALL_REAL, "mock"):
        assert providers[key]["implemented"] is True, key


def test_real_providers_degrade_without_sdk_or_creds():
    # Real controllers try to import their SDK / use creds at invoke time; without
    # them in the test env the service returns an error envelope (HTTP 200,
    # status=error) instead of raising.
    for key in ALL_REAL:
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
