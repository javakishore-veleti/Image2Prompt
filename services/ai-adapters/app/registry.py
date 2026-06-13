from __future__ import annotations

from .config import settings
from .controllers.anthropic_ctrl import AnthropicController
from .controllers.base import ProviderController
from .controllers.bedrock import BedrockController
from .controllers.cohere_ctrl import CohereController
from .controllers.crewai_ctrl import CrewAIController
from .controllers.google_ctrl import GoogleController
from .controllers.langgraph_ctrl import LangGraphController
from .controllers.litellm_ctrl import LiteLLMController
from .controllers.llamaindex_ctrl import LlamaIndexController
from .controllers.microsoft_ctrl import MicrosoftController
from .controllers.mistral_ctrl import MistralController
from .controllers.mock import MockController
from .controllers.ollama_ctrl import OllamaController
from .controllers.openai_ctrl import OpenAIController
from .controllers.openrouter_ctrl import OpenRouterController
from .controllers.strands import StrandsController


def build_registry() -> dict[str, ProviderController]:
    """Construct the provider_key -> controller map.

    The global enable/disable flag lives in admin-service; this registry only
    decides which controllers exist and which are actually implemented. Vendor
    SDKs are imported lazily inside each controller, so missing creds/SDKs surface
    as a per-request error envelope rather than breaking startup.
    """
    controllers: list[ProviderController] = [
        BedrockController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        MockController(),
        StrandsController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        LangGraphController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        CrewAIController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        LlamaIndexController(region=settings.aws_region, model_id=settings.bedrock_model_id),
        GoogleController(api_key=settings.google_api_key, model=settings.google_model),
        OpenAIController(api_key=settings.openai_api_key, model=settings.openai_model),
        AnthropicController(api_key=settings.anthropic_api_key, model=settings.anthropic_model),
        MicrosoftController(
            endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            deployment=settings.azure_openai_deployment,
        ),
        MistralController(api_key=settings.mistral_api_key, model=settings.mistral_model),
        CohereController(api_key=settings.cohere_api_key, model=settings.cohere_model),
        OllamaController(base_url=settings.ollama_base_url, model=settings.ollama_model),
        OpenRouterController(),
        LiteLLMController(),
    ]
    return {c.key: c for c in controllers}


REGISTRY: dict[str, ProviderController] = build_registry()
