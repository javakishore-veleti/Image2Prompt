from __future__ import annotations

from .config import settings
from .controllers.base import ProviderController
from .controllers.bedrock import BedrockController
from .controllers.mock import MockController
from .controllers.strands import StrandsController
from .controllers.crewai_ctrl import CrewAIController
from .controllers.langgraph_ctrl import LangGraphController
from .controllers.llamaindex_ctrl import LlamaIndexController
from .controllers.stubs import (
    AnthropicController,
    GoogleController,
    MicrosoftController,
    OpenAIController,
)


def build_registry() -> dict[str, ProviderController]:
    """Construct the provider_key -> controller map.

    The global enable/disable flag lives in admin-service; this registry only
    decides which controllers exist and which are actually implemented.
    """
    controllers: list[ProviderController] = [
        BedrockController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        MockController(),
        StrandsController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        AnthropicController(),
        OpenAIController(),
        GoogleController(),
        MicrosoftController(),
        LangGraphController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        CrewAIController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        LlamaIndexController(region=settings.aws_region, model_id=settings.bedrock_model_id),
    ]
    return {c.key: c for c in controllers}


REGISTRY: dict[str, ProviderController] = build_registry()
