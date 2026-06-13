"""Tests for the CAF secret client: env provider, bulk, disabled toggle, and
graceful failure when a cloud SDK is unavailable."""

import os

from img2pmpt_caf_secret import GetSecretReq, GetSecretsReq
from img2pmpt_caf_secret.client.secret_client import SecretClient
from img2pmpt_caf_secret.config import CafSecretSettings


def _client(**kw) -> SecretClient:
    return SecretClient(CafSecretSettings(**kw))


def test_env_provider_reads_environment():
    os.environ["CAF_TEST_KEY"] = "hello"
    c = _client(provider="env", env_enabled=True)
    r = c.get_secret_by_key(GetSecretReq(key="CAF_TEST_KEY"))
    assert r.success and r.found and r.value == "hello"
    assert c.provider_name == "env"


def test_env_provider_missing_returns_default_not_found():
    c = _client(provider="env", env_enabled=True)
    r = c.get_secret_by_key(GetSecretReq(key="CAF_DEFINITELY_MISSING", default="fallback"))
    assert r.success and not r.found and r.value == "fallback"


def test_bulk_lookup_tracks_missing():
    os.environ["CAF_A"] = "1"
    c = _client(provider="env", env_enabled=True)
    r = c.get_secrets_by_keys(GetSecretsReq(keys=["CAF_A", "CAF_B_MISSING"]))
    assert r.success
    assert r.values["CAF_A"] == "1"
    assert "CAF_B_MISSING" in r.missing


def test_disabled_provider_fails_safely():
    c = _client(provider="env", env_enabled=False)
    r = c.get_secret_by_key(GetSecretReq(key="ANY", default="d"))
    assert not r.success
    assert r.error_code == "provider_disabled"
    assert r.value == "d"  # default still returned, no exception


def test_cloud_provider_without_sdk_fails_safely():
    # aws selected + enabled but boto3 not installed -> graceful error, no raise.
    c = _client(provider="aws", aws_enabled=True)
    r = c.get_secret_by_key(GetSecretReq(key="ANY"))
    assert not r.success
    assert r.error_code == "provider_error"


def test_unknown_provider_fails_safely():
    c = _client(provider="vault", env_enabled=True)
    r = c.get_secret_by_key(GetSecretReq(key="ANY"))
    assert not r.success
    assert r.error_code in ("provider_disabled", "unknown_provider")
