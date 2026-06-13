from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.security import hash_password

from .config import settings
from .models import AdminUser, Provider

# Registry of providers the platform knows about. bedrock + mock enabled by
# default so the end-to-end flow works with zero cloud credentials.
DEFAULT_PROVIDERS = [
    {"key": "bedrock", "name": "AWS Bedrock (Claude)", "category": "aws", "enabled": True},
    {"key": "mock", "name": "Mock Provider (offline dev)", "category": "dev", "enabled": True},
    {"key": "strands", "name": "AWS Strands Agents", "category": "framework", "enabled": False},
    {"key": "anthropic", "name": "Anthropic API", "category": "anthropic", "enabled": False},
    {"key": "openai", "name": "OpenAI SDK", "category": "openai", "enabled": False},
    {"key": "google", "name": "Google GenAI SDK", "category": "google", "enabled": False},
    {"key": "microsoft", "name": "Microsoft AI SDK", "category": "microsoft", "enabled": False},
    {"key": "langgraph", "name": "LangGraph", "category": "framework", "enabled": False},
    {"key": "crewai", "name": "CrewAI", "category": "framework", "enabled": False},
    {"key": "llamaindex", "name": "LlamaIndex", "category": "framework", "enabled": False},
    {"key": "mistral", "name": "Mistral (Pixtral)", "category": "mistral", "enabled": False},
    {"key": "cohere", "name": "Cohere (Aya Vision)", "category": "cohere", "enabled": False},
    {"key": "ollama", "name": "Ollama (local)", "category": "local", "enabled": False},
    {"key": "openrouter", "name": "OpenRouter", "category": "router", "enabled": False},
    {"key": "litellm", "name": "LiteLLM", "category": "router", "enabled": False},
]


def seed(session: Session) -> None:
    _seed_admin(session)
    _seed_providers(session)
    session.commit()


def _seed_admin(session: Session) -> None:
    existing = session.scalar(select(AdminUser).where(AdminUser.email == settings.admin_email))
    if existing is None:
        session.add(
            AdminUser(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                role="superadmin",
            )
        )


def _seed_providers(session: Session) -> None:
    existing_keys = set(session.scalars(select(Provider.key)).all())
    for p in DEFAULT_PROVIDERS:
        if p["key"] not in existing_keys:
            session.add(Provider(**p, config={}))
