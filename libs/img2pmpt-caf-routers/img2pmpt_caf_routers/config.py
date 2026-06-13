"""Router settings. Per-router feature toggles use the ``CAF_ROUTERS_*`` names;
API keys/models use their plain env names so they flow from the same .env / CAF
secret bundle the rest of the app uses."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CafRoutersSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Feature toggles (a router must be enabled to be used).
    caf_routers_openrouter_enabled: bool = True
    caf_routers_litellm_enabled: bool = True

    # OpenRouter (OpenAI-compatible).
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # LiteLLM routes by model prefix; reads the backend provider's key from env.
    litellm_model: str = "gpt-4o"

    def enabled_for(self, router: str) -> bool:
        return {
            "openrouter": self.caf_routers_openrouter_enabled,
            "litellm": self.caf_routers_litellm_enabled,
        }.get(router, False)
