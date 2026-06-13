"""Base request/response objects for the layered architecture.

Every facade / service / DAO method takes exactly one ``*Req`` and returns one
``*Resp`` — no loose positional arguments. These bases are keyword-only
dataclasses so subclasses can add required fields without dataclass field-order
errors. Internal layers use dataclasses (they may carry ORM entities); the API
layer maps HTTP pydantic models to/from these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(kw_only=True)
class BaseReq:
    # Correlation id flows through the layers and onto spans/log records.
    correlation_id: Optional[str] = None


@dataclass(kw_only=True)
class BaseResp:
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    @classmethod
    def failure(cls, *, error_code: str, error_message: str, **kwargs: Any) -> "BaseResp":
        return cls(success=False, error_code=error_code, error_message=error_message, **kwargs)


@dataclass(kw_only=True)
class ErrorInfo:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
