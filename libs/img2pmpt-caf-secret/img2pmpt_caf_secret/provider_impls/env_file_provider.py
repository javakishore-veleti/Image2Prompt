"""Default provider: reads from process env, optionally overlaying a .env file."""

from __future__ import annotations

import os

from ..client.dtos import GetSecretReq, GetSecretResp
from ..config import CafSecretSettings
from .interfaces import BaseProvider


def _parse_env_file(path: str) -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


class EnvFileProvider(BaseProvider):
    name = "env"

    def __init__(self, settings: CafSecretSettings) -> None:
        self._overlay = _parse_env_file(settings.env_file_path) if settings.env_file_path else {}

    def get_secret_by_key(self, req: GetSecretReq) -> GetSecretResp:
        value = self._overlay.get(req.key, os.environ.get(req.key))
        if value is None:
            return GetSecretResp(key=req.key, value=req.default, found=False)
        return GetSecretResp(key=req.key, value=value, found=True)
