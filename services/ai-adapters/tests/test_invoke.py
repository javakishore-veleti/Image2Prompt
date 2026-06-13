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


def test_unknown_provider_404():
    r = client.post(
        "/invoke",
        json={"provider_key": "does-not-exist", "request_id": "req-3", "image_base64": IMG_B64},
    )
    assert r.status_code == 404
