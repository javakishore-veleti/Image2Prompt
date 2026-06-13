"""Orchestration test for image-processing: store -> resolve -> dispatch ->
persist -> list prompts. Remote services (admin/customer/ai-adapters) are
stubbed so no network is needed; runs on SQLite."""

import asyncio
import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_db_path}"
os.environ["LOCAL_STORAGE_DIR"] = tempfile.mkdtemp()

from app.db import Base, db  # noqa: E402
from app.di import _image_facade  # noqa: E402
from app.dtos.internal_dtos import (  # noqa: E402
    DispatchResp,
    EnabledProvidersResp,
    ListEnabledProvidersReq,
    ListPromptsReq,
    ProcessImageReq,
    ResolveProvidersResp,
)

db.bootstrap(base=Base, settings=type("S", (), {"run_migrations_on_startup": False})())


def _stub_resolve(*_a, **_k):
    async def _inner(req):
        return ResolveProvidersResp(
            selected=["mock"], provider_id_map={"mock": "pid-1"}, config_map={}, storage_backend="local"
        )
    return _inner


def _stub_dispatch():
    async def _inner(req):
        return DispatchResp(payload={"status": "success", "output_text": "a prompt", "latency_ms": 3})
    return _inner


def test_process_image_and_list_prompts(monkeypatch):
    monkeypatch.setattr(_image_facade.resolution_service, "resolve", _stub_resolve())
    monkeypatch.setattr(_image_facade.dispatch_service, "invoke", _stub_dispatch())

    session = db.SessionLocal()
    try:
        resp = asyncio.run(
            _image_facade.process_image(
                ProcessImageReq(
                    db=session,
                    customer_id="cust-1",
                    image_bytes=b"fake-bytes",
                    content_type="image/png",
                    filename="x.png",
                    instruction="describe",
                )
            )
        )
        assert resp.success
        assert resp.request.status == "completed"
        assert resp.request.providers[0].output_text == "a prompt"

        prompts = _image_facade.list_prompts(ListPromptsReq(db=session, customer_id="cust-1"))
        assert len(prompts.items) == 1
        assert prompts.items[0].output_text == "a prompt"
    finally:
        session.close()


def test_list_providers_delegates_to_resolution(monkeypatch):
    async def _enabled(req):
        return EnabledProvidersResp(providers=[{"key": "mock", "name": "Mock"}, {"key": "bedrock", "name": "Bedrock"}])

    monkeypatch.setattr(_image_facade.resolution_service, "list_enabled", _enabled)
    resp = asyncio.run(_image_facade.list_providers(ListEnabledProvidersReq()))
    assert resp.success
    assert {p["key"] for p in resp.providers} == {"mock", "bedrock"}


def test_no_providers_returns_error(monkeypatch):
    async def _empty(req):
        return ResolveProvidersResp(selected=[], provider_id_map={}, config_map={}, storage_backend="local")

    monkeypatch.setattr(_image_facade.resolution_service, "resolve", _empty)
    session = db.SessionLocal()
    try:
        resp = asyncio.run(
            _image_facade.process_image(
                ProcessImageReq(
                    db=session,
                    customer_id="cust-2",
                    image_bytes=b"x",
                    content_type="image/png",
                    filename="x.png",
                    instruction="describe",
                )
            )
        )
        assert not resp.success
        assert resp.error_code == "no_providers"
    finally:
        session.close()
