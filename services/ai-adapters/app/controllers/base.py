from __future__ import annotations

from abc import ABC, abstractmethod

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp


class ProviderController(ABC):
    """Base class for a provider controller.

    Each provider (Bedrock, Anthropic, OpenAI, ...) turns an image + instruction
    into a generated prompt. Like every layer method, ``invoke`` takes one
    ``*Req`` and returns one ``*Resp``. ``implemented`` lets the registry
    advertise which providers are live vs. registered stubs.
    """

    key: str = "abstract"
    implemented: bool = False

    @abstractmethod
    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp: ...
