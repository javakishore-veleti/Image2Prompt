from __future__ import annotations

from abc import ABC, abstractmethod

from ..dtos import internal_dtos as dto


class IImageFacade(ABC):
    @abstractmethod
    async def process_image(self, req: "dto.ProcessImageReq") -> "dto.ProcReqResp": ...

    @abstractmethod
    async def process_from_connection(self, req: "dto.ProcessFromConnectionReq") -> "dto.ProcReqResp": ...

    @abstractmethod
    def list_requests(self, req: "dto.ListRequestsReq") -> "dto.ProcReqListResp": ...

    @abstractmethod
    def get_request(self, req: "dto.GetRequestReq") -> "dto.ProcReqResp": ...

    @abstractmethod
    def list_prompts(self, req: "dto.ListPromptsReq") -> "dto.PromptListResp": ...

    @abstractmethod
    async def list_providers(self, req: "dto.ListEnabledProvidersReq") -> "dto.EnabledProvidersResp": ...

    @abstractmethod
    def stats(self, req: "dto.StatsReq") -> "dto.StatsResp": ...
