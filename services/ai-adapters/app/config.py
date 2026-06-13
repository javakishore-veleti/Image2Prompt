from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class AiAdaptersSettings(ServiceSettings):
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    anthropic_api_key: str = ""


settings = AiAdaptersSettings()
