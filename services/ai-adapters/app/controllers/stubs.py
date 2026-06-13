from __future__ import annotations

from ..dtos.internal_dtos import ProviderInvokeReq, ProviderInvokeResp
from .base import ProviderController


class _StubController(ProviderController):
    """Registered but not implemented. Wired so it lights up when built out."""

    implemented = False

    async def invoke(self, req: ProviderInvokeReq) -> ProviderInvokeResp:
        raise NotImplementedError(f"Provider '{self.key}' is not implemented yet")


class AnthropicController(_StubController):
    key = "anthropic"


class OpenAIController(_StubController):
    key = "openai"


class GoogleController(_StubController):
    key = "google"


class MicrosoftController(_StubController):
    key = "microsoft"


class LangGraphController(_StubController):
    key = "langgraph"


class CrewAIController(_StubController):
    key = "crewai"


class LlamaIndexController(_StubController):
    key = "llamaindex"
