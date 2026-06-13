"""Tests for the CAF router client: routing selection, disabled toggle, unknown
router, and graceful failure when a router SDK/key is unavailable."""

from img2pmpt_caf_routers import RouteReq
from img2pmpt_caf_routers.client.router_client import RouterClient
from img2pmpt_caf_routers.config import CafRoutersSettings

IMG = "ZmFrZQ=="  # base64 "fake"


def _client(**kw) -> RouterClient:
    return RouterClient(CafRoutersSettings(**kw))


def test_available_lists_routers():
    names = {r.name for r in _client().available()}
    assert {"openrouter", "litellm"} <= names


def test_unknown_router_fails_safely():
    r = _client().route(RouteReq(router="nope", instruction="x", image_base64=IMG))
    assert not r.success and r.error_code == "unknown_router"


def test_disabled_router_fails_safely():
    c = _client(caf_routers_openrouter_enabled=False)
    r = c.route(RouteReq(router="openrouter", instruction="x", image_base64=IMG))
    assert not r.success and r.error_code == "router_disabled"


def test_openrouter_without_key_fails_safely():
    c = _client(openrouter_api_key="")
    r = c.route(RouteReq(router="openrouter", instruction="x", image_base64=IMG))
    assert not r.success
    assert r.error_code in ("not_configured", "provider_error")


def test_litellm_without_sdk_or_key_fails_safely():
    r = _client().route(RouteReq(router="litellm", instruction="x", image_base64=IMG))
    assert not r.success
    assert r.error_code == "provider_error"
