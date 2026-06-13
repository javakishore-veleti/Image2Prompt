from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class AiAdaptersSettings(ServiceSettings):
    service_name: str = "ai-adapters"

    # AWS Bedrock (used directly and by the framework providers + Strands).
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"

    # Direct vendor SDKs (keys come from env / the CAF secret store).
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    google_api_key: str = ""
    google_model: str = "gemini-1.5-flash"

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-06-01"
    azure_openai_deployment: str = "gpt-4o"


settings = AiAdaptersSettings()
