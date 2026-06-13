"""HTTP request/response models (pydantic) at the API boundary."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    email: str
    role: str = "admin"


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    key: str
    name: str
    category: str
    enabled: bool
    config: dict[str, Any] = {}


class ProviderCreate(BaseModel):
    key: str
    name: str
    category: str = "generic"
    enabled: bool = False
    config: dict[str, Any] = {}


class ProviderUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class CustomerOut(BaseModel):
    id: str
    email: str
    name: str | None = None
    status: str | None = None
