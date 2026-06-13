"""HTTP request/response models (pydantic) at the API boundary. Controllers map
these to/from the internal ``*Req``/``*Resp`` dataclasses."""

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


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    customer_id: str
    email: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


class MessageResponse(BaseModel):
    message: str


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    name: str | None = None
    status: str
    email_verified: bool = False


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: Any
    action: str
    target: str | None = None
    detail: dict[str, Any] = {}


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


class ConnectRequest(BaseModel):
    provider: str


class ConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    provider: str
    display_name: str
    account_email: str | None = None
    status: str


class FileOut(BaseModel):
    id: str
    name: str
    mime_type: str
    size: int
