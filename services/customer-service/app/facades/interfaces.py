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


class IProfileFacade(ABC):
    @abstractmethod
    def get_me(self, req: "dto.GetByIdReq") -> "dto.CustomerResp": ...

    @abstractmethod
    def get_preferences(self, req: "dto.GetPrefsReq") -> "dto.PrefsResp": ...

    @abstractmethod
    def update_preferences(self, req: "dto.UpdatePrefsReq") -> "dto.PrefsResp": ...


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
    def get_billing(self, req: "dto.BillingReq") -> "dto.BillingResp": ...


class IConnectionsFacade(ABC):
    @abstractmethod
    def connect(self, req: "dto.ConnectReq") -> "dto.ConnectionResp": ...

    @abstractmethod
    def list_connections(self, req: "dto.ListConnectionsReq") -> "dto.ConnectionListResp": ...

    @abstractmethod
    def disconnect(self, req: "dto.DisconnectReq") -> "dto.ConnectionResp": ...

    @abstractmethod
    def list_files(self, req: "dto.ListFilesReq") -> "dto.FileListResp": ...


class IInternalFacade(ABC):
    @abstractmethod
    def search_customers(self, req: "dto.SearchCustomersReq") -> "dto.CustomerListResp": ...

    @abstractmethod
    def get_customer(self, req: "dto.GetByIdReq") -> "dto.CustomerResp": ...

    @abstractmethod
    def get_preferences(self, req: "dto.GetPrefsReq") -> "dto.PrefsResp": ...
