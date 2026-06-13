"""Facade interfaces. Controllers depend on these ABCs (autowired via di.py),
never on concrete classes."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..dtos import internal_dtos as dto


class IAuthFacade(ABC):
    @abstractmethod
    def signup(self, req: "dto.SignupReq") -> "dto.AuthResp": ...

    @abstractmethod
    def login(self, req: "dto.LoginReq") -> "dto.AuthResp": ...

    @abstractmethod
    def refresh(self, req: "dto.RefreshReq") -> "dto.AuthResp": ...

    @abstractmethod
    def logout(self, req: "dto.LogoutReq") -> "dto.LogoutResp": ...

    @abstractmethod
    def request_password_reset(self, req: "dto.RequestPasswordResetReq") -> "dto.MessageResp": ...

    @abstractmethod
    def reset_password(self, req: "dto.ResetPasswordReq") -> "dto.MessageResp": ...

    @abstractmethod
    def send_verification_email(self, req: "dto.SendVerificationReq") -> "dto.MessageResp": ...

    @abstractmethod
    def verify_email(self, req: "dto.VerifyEmailReq") -> "dto.MessageResp": ...


class IProfileFacade(ABC):
    @abstractmethod
    def get_me(self, req: "dto.GetByIdReq") -> "dto.CustomerResp": ...

    @abstractmethod
    def get_preferences(self, req: "dto.GetPrefsReq") -> "dto.PrefsResp": ...

    @abstractmethod
    def update_preferences(self, req: "dto.UpdatePrefsReq") -> "dto.PrefsResp": ...

    @abstractmethod
    def list_activity(self, req: "dto.ListActivityReq") -> "dto.ActivityListResp": ...

    @abstractmethod
    def unlock_account(self, req: "dto.UnlockAccountReq") -> "dto.MessageResp": ...


class IProjectsFacade(ABC):
    @abstractmethod
    def list_projects(self, req: "dto.ListProjectsReq") -> "dto.ProjectListResp": ...

    @abstractmethod
    def create_project(self, req: "dto.CreateProjectReq") -> "dto.ProjectResp": ...

    @abstractmethod
    def get_project(self, req: "dto.GetProjectReq") -> "dto.ProjectResp": ...


class IPaymentsFacade(ABC):
    @abstractmethod
    def get_settings(self, req: "dto.GetPaymentReq") -> "dto.PaymentResp": ...

    @abstractmethod
    def update_settings(self, req: "dto.UpdatePaymentReq") -> "dto.PaymentResp": ...

    @abstractmethod
    def create_setup_intent(self, req: "dto.SetupIntentReq") -> "dto.SetupIntentResp": ...

    @abstractmethod
    def get_billing(self, req: "dto.BillingReq") -> "dto.BillingResp": ...


class IConnectionsFacade(ABC):
    @abstractmethod
    def connect(self, req: "dto.ConnectReq") -> "dto.ConnectionResp": ...

    @abstractmethod
    def google_authorize(self, req: "dto.GoogleAuthorizeReq") -> "dto.GoogleAuthorizeResp": ...

    @abstractmethod
    def google_callback(self, req: "dto.GoogleCallbackReq") -> "dto.ConnectionResp": ...

    @abstractmethod
    def onedrive_authorize(self, req: "dto.GoogleAuthorizeReq") -> "dto.GoogleAuthorizeResp": ...

    @abstractmethod
    def onedrive_callback(self, req: "dto.GoogleCallbackReq") -> "dto.ConnectionResp": ...

    @abstractmethod
    def list_connections(self, req: "dto.ListConnectionsReq") -> "dto.ConnectionListResp": ...

    @abstractmethod
    def disconnect(self, req: "dto.DisconnectReq") -> "dto.ConnectionResp": ...

    @abstractmethod
    def list_files(self, req: "dto.ListFilesReq") -> "dto.FileListResp": ...

    @abstractmethod
    def download_file(self, req: "dto.DownloadFileReq") -> "dto.FileContentResp": ...

    @abstractmethod
    def reencrypt_tokens(self, req: "dto.ReencryptTokensReq") -> "dto.ReencryptResp": ...

    @abstractmethod
    def rotation_status(self, req: "dto.RotationStatusReq") -> "dto.RotationStatusResp": ...


class IInternalFacade(ABC):
    @abstractmethod
    def search_customers(self, req: "dto.SearchCustomersReq") -> "dto.CustomerListResp": ...

    @abstractmethod
    def count_customers(self, req: "dto.CountCustomersReq") -> "dto.CountResp": ...

    @abstractmethod
    def get_customer(self, req: "dto.GetByIdReq") -> "dto.CustomerResp": ...

    @abstractmethod
    def get_preferences(self, req: "dto.GetPrefsReq") -> "dto.PrefsResp": ...
