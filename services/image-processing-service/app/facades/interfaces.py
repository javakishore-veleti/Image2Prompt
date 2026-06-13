from __future__ import annotations

from abc import ABC, abstractmethod

from ..dtos import internal_dtos as dto


class IImageFacade(ABC):
    @abstractmethod
    async def process_image(self, req: "dto.ProcessImageReq") -> "dto.ProcReqResp": ...

    @abstractmethod
    def list_requests(self, req: "dto.ListRequestsReq") -> "dto.ProcReqListResp": ...

    @abstractmethod
    def get_request(self, req: "dto.GetRequestReq") -> "dto.ProcReqResp": ...

    @abstractmethod
    def list_prompts(self, req: "dto.ListPromptsReq") -> "dto.PromptListResp": ...
