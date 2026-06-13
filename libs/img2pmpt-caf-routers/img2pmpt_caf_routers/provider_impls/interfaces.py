"""Router provider interface + a shared base."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..client.dtos import RouteReq, RouteResp


class IRouterProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def route(self, req: RouteReq) -> RouteResp: ...


def data_uri(media_type: str, image_base64: str) -> str:
    return f"data:{media_type or 'image/png'};base64,{image_base64}"
