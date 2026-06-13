from __future__ import annotations

from .base import InvokeResult, ProviderController


class _StubController(ProviderController):
    """Registered but not implemented. Wired so it lights up when built out."""

    implemented = False

    async def invoke(
        self, *, request_id: str, instruction: str, image_base64: str, media_type: str, config: dict
    ) -> InvokeResult:
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
