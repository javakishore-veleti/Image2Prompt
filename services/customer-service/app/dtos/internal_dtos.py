"""Internal req/resp dataclasses passed between facade -> service -> dao.

Every layer method takes exactly one ``*Req`` and returns one ``*Resp``. The DB
Session travels inside the Req (shared-nothing: singletons hold no session).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from image2prompt_shared.dtos import BaseReq, BaseResp

from ..models import AuditLog, Connection, Customer, CustomerPreference, PaymentSettings, Project


# --- auth ---
@dataclass(kw_only=True)
class SignupReq(BaseReq):
    db: Session
    email: str
    password: str
    name: Optional[str] = None


@dataclass(kw_only=True)
class LoginReq(BaseReq):
    db: Session
    email: str
    password: str


@dataclass(kw_only=True)
class RefreshReq(BaseReq):
    db: Session
    refresh_token: str


@dataclass(kw_only=True)
class LogoutReq(BaseReq):
    db: Session
    refresh_token: str


@dataclass(kw_only=True)
class LogoutResp(BaseResp):
    pass


@dataclass(kw_only=True)
class AuthResp(BaseResp):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    customer_id: Optional[str] = None
    email: Optional[str] = None


# --- password reset / email verification ---
@dataclass(kw_only=True)
class RequestPasswordResetReq(BaseReq):
    db: Session
    email: str


@dataclass(kw_only=True)
class ResetPasswordReq(BaseReq):
    db: Session
    token: str
    new_password: str


@dataclass(kw_only=True)
class SendVerificationReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class VerifyEmailReq(BaseReq):
    db: Session
    token: str


@dataclass(kw_only=True)
class MessageResp(BaseResp):
    message: str = ""


# --- audit / account activity ---
@dataclass(kw_only=True)
class RecordAuditReq(BaseReq):
    db: Session
    action: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None
    target: Optional[str] = None
    detail: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class ListActivityReq(BaseReq):
    db: Session
    customer_id: str
    customer_email: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(kw_only=True)
class UnlockAccountReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class ActivityListResp(BaseResp):
    entries: list[AuditLog] = field(default_factory=list)
    total: int = 0


# --- customer crud ---
@dataclass(kw_only=True)
class GetByEmailReq(BaseReq):
    db: Session
    email: str


@dataclass(kw_only=True)
class GetByIdReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class CreateCustomerReq(BaseReq):
    db: Session
    email: str
    password_hash: str
    name: Optional[str] = None


@dataclass(kw_only=True)
class CustomerResp(BaseResp):
    customer: Optional[Customer] = None


@dataclass(kw_only=True)
class SearchCustomersReq(BaseReq):
    db: Session
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(kw_only=True)
class CustomerListResp(BaseResp):
    customers: list[Customer] = field(default_factory=list)


@dataclass(kw_only=True)
class CountCustomersReq(BaseReq):
    db: Session


@dataclass(kw_only=True)
class CountResp(BaseResp):
    count: int = 0


# --- preferences ---
@dataclass(kw_only=True)
class GetPrefsReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class UpdatePrefsReq(BaseReq):
    db: Session
    customer_id: str
    default_provider_keys: Optional[list[str]] = None
    storage_backend: Optional[str] = None
    prefs: Optional[dict] = None


@dataclass(kw_only=True)
class PrefsResp(BaseResp):
    preference: Optional[CustomerPreference] = None


# --- projects ---
@dataclass(kw_only=True)
class ListProjectsReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class CreateProjectReq(BaseReq):
    db: Session
    customer_id: str
    name: str
    meta: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class GetProjectReq(BaseReq):
    db: Session
    customer_id: str
    project_id: str


@dataclass(kw_only=True)
class ProjectResp(BaseResp):
    project: Optional[Project] = None


@dataclass(kw_only=True)
class ProjectListResp(BaseResp):
    projects: list[Project] = field(default_factory=list)


# --- payments ---
@dataclass(kw_only=True)
class GetPaymentReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class UpdatePaymentReq(BaseReq):
    db: Session
    customer_id: str
    data: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class PaymentResp(BaseResp):
    settings: Optional[PaymentSettings] = None
    configured: bool = False
    stripe_customer_id: Optional[str] = None


@dataclass(kw_only=True)
class SetupIntentReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class SetupIntentResp(BaseResp):
    configured: bool = False
    client_secret: Optional[str] = None


@dataclass(kw_only=True)
class BillingReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class BillingResp(BaseResp):
    configured: bool = False
    receipts: list = field(default_factory=list)
    balance_due: float = 0.0
    currency: str = "usd"


# --- connections (external file systems; mock OAuth for now) ---
@dataclass(kw_only=True)
class ConnectReq(BaseReq):
    db: Session
    customer_id: str
    provider: str


@dataclass(kw_only=True)
class ListConnectionsReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class DisconnectReq(BaseReq):
    db: Session
    customer_id: str
    connection_id: str


@dataclass(kw_only=True)
class CreateConnectionReq(BaseReq):
    db: Session
    customer_id: str
    provider: str
    display_name: str
    account_email: Optional[str] = None
    meta: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class GetConnectionReq(BaseReq):
    db: Session
    customer_id: str
    connection_id: str


@dataclass(kw_only=True)
class ListFilesReq(BaseReq):
    db: Session
    customer_id: str
    connection_id: str
    search: Optional[str] = None


@dataclass(kw_only=True)
class GoogleAuthorizeReq(BaseReq):
    db: Session
    customer_id: str


@dataclass(kw_only=True)
class GoogleAuthorizeResp(BaseResp):
    configured: bool = False
    authorize_url: Optional[str] = None


@dataclass(kw_only=True)
class GoogleCallbackReq(BaseReq):
    db: Session
    code: str
    state: str


@dataclass(kw_only=True)
class ConnectionResp(BaseResp):
    connection: Optional[Connection] = None


@dataclass(kw_only=True)
class ConnectionListResp(BaseResp):
    connections: list[Connection] = field(default_factory=list)


@dataclass(kw_only=True)
class DownloadFileReq(BaseReq):
    db: Session
    customer_id: str
    connection_id: str
    file_id: str


@dataclass(kw_only=True)
class FileContentResp(BaseResp):
    content: bytes = b""
    content_type: str = "application/octet-stream"


@dataclass(kw_only=True)
class FileItem:
    id: str
    name: str
    mime_type: str
    size: int


@dataclass(kw_only=True)
class FileListResp(BaseResp):
    files: list[FileItem] = field(default_factory=list)


@dataclass(kw_only=True)
class ReencryptTokensReq(BaseReq):
    db: Session


@dataclass(kw_only=True)
class ReencryptResp(BaseResp):
    count: int = 0


@dataclass(kw_only=True)
class RotationStatusReq(BaseReq):
    db: Session


@dataclass(kw_only=True)
class RotationStatusResp(BaseResp):
    total: int = 0  # connections with encrypted tokens
    stale: int = 0  # of those, not under the current key
