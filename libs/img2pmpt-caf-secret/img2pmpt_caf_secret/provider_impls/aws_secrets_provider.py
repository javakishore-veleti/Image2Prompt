"""AWS Secrets Manager provider. The secret named ``aws_secret_name`` holds a
JSON object of key->value; it's fetched once and cached. boto3 imported lazily."""

from __future__ import annotations

import json

from ..client.dtos import GetSecretReq, GetSecretResp, GetSecretsReq, GetSecretsResp
from ..config import CafSecretSettings
from .interfaces import BaseProvider


class AwsSecretsManagerProvider(BaseProvider):
    name = "aws"

    def __init__(self, settings: CafSecretSettings) -> None:
        self._region = settings.aws_region
        self._secret_name = settings.aws_secret_name
        self._bundle: dict[str, str] | None = None
        self._load_error: str | None = None

    def _bundle_dict(self) -> dict[str, str] | None:
        if self._bundle is not None or self._load_error is not None:
            return self._bundle
        try:
            import boto3  # lazy: only needed when AWS is the active provider

            client = boto3.client("secretsmanager", region_name=self._region)
            resp = client.get_secret_value(SecretId=self._secret_name)
            raw = resp.get("SecretString") or "{}"
            self._bundle = json.loads(raw)
        except Exception as exc:  # SDK missing / access denied / bad JSON
            self._load_error = str(exc)
        return self._bundle

    def get_secret_by_key(self, req: GetSecretReq) -> GetSecretResp:
        bundle = self._bundle_dict()
        if bundle is None:
            return GetSecretResp(
                success=False, key=req.key, error_code="provider_error", error_message=self._load_error
            )
        if req.key in bundle:
            return GetSecretResp(key=req.key, value=bundle[req.key], found=True)
        return GetSecretResp(key=req.key, value=req.default, found=False)

    def get_secrets_by_keys(self, req: GetSecretsReq) -> GetSecretsResp:
        bundle = self._bundle_dict()
        if bundle is None:
            return GetSecretsResp(
                success=False, error_code="provider_error", error_message=self._load_error
            )
        values: dict[str, str | None] = {}
        missing: list[str] = []
        for key in req.keys:
            if key in bundle:
                values[key] = bundle[key]
            else:
                values[key] = None
                missing.append(key)
        return GetSecretsResp(values=values, missing=missing)
