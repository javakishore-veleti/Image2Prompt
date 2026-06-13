"""Request/response objects for the secret client (keyword-only dataclasses).

CAF is standalone (no dependency on the app's shared lib), so it defines its own
minimal Req/Resp bases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(kw_only=True)
class BaseResp:
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass(kw_only=True)
class GetSecretReq:
    key: str
    default: Optional[str] = None


@dataclass(kw_only=True)
class GetSecretResp(BaseResp):
    key: str = ""
    value: Optional[str] = None
    found: bool = False


@dataclass(kw_only=True)
class GetSecretsReq:
    keys: list[str]


@dataclass(kw_only=True)
class GetSecretsResp(BaseResp):
    values: dict[str, Optional[str]] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
