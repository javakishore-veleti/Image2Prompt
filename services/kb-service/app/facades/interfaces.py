"""Facade interface. Controllers depend on this ABC (wired via di.py)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..dtos import internal_dtos as dto


class IKbFacade(ABC):
    @abstractmethod
    def create_group(self, req: "dto.CreateGroupReq") -> "dto.GroupResp": ...

    @abstractmethod
    def list_groups(self, req: "dto.ListGroupsReq") -> "dto.GroupListResp": ...

    @abstractmethod
    async def create_kb(self, req: "dto.CreateKbReq") -> "dto.KbResp": ...

    @abstractmethod
    def list_kbs(self, req: "dto.ListKbsReq") -> "dto.KbListResp": ...

    @abstractmethod
    def get_kb(self, req: "dto.GetKbReq") -> "dto.KbResp": ...

    @abstractmethod
    def list_docs(self, req: "dto.ListDocsReq") -> "dto.DocListResp": ...

    @abstractmethod
    async def ingest(self, req: "dto.IngestReq") -> "dto.IngestResp": ...

    @abstractmethod
    async def query(self, req: "dto.QueryReq") -> "dto.QueryResp": ...

    @abstractmethod
    def usage(self, req: "dto.UsageReq") -> "dto.UsageResp": ...

    @abstractmethod
    def delete_kb(self, req: "dto.DeleteKbReq") -> "dto.DeleteResp": ...

    @abstractmethod
    def delete_group(self, req: "dto.DeleteGroupReq") -> "dto.DeleteResp": ...
