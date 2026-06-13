from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_id: str
    email: str


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str | None = None
    status: str


class PreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    default_provider_keys: list[str] = []
    storage_backend: str = "local"
    prefs: dict[str, Any] = {}


class PreferenceUpdate(BaseModel):
    default_provider_keys: list[str] | None = None
    storage_backend: str | None = None
    prefs: dict[str, Any] | None = None


class ProjectCreate(BaseModel):
    name: str
    meta: dict[str, Any] = {}


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    name: str
    meta: dict[str, Any] = {}


class PaymentSettingsUpdate(BaseModel):
    data: dict[str, Any] = {}


class PaymentSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    data: dict[str, Any] = {}
