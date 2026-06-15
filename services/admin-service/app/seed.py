from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from image2prompt_shared.security import hash_password

from .config import settings
from .models import AdminUser, Provider, SubscriptionPlan

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


# Starter plans so a fresh deploy can assign subscriptions / create KBs out of the
# box. ``stacks`` is a list of {stack, monthly_cost} — the stacks present are the
# ones the plan allows; the free local stacks (pgvector, chroma) cost 0. Admins can
# edit these or add more from the Subscriptions UI. Seeded only when no plan exists,
# so admin edits are never overwritten on restart.
DEFAULT_PLANS = [
    {
        "name": "Starter",
        "description": "Self-serve, locally-runnable vector stores to get started.",
        "stacks": [
            {"stack": "pgvector", "monthly_cost": 0},
            {"stack": "chroma", "monthly_cost": 0},
        ],
    },
    {
        "name": "Professional",
        "description": "Managed cloud vector stores for production workloads.",
        "stacks": [
            {"stack": "pgvector", "monthly_cost": 0},
            {"stack": "chroma", "monthly_cost": 0},
            {"stack": "pinecone", "monthly_cost": 49},
            {"stack": "weaviate", "monthly_cost": 49},
            {"stack": "mongodb", "monthly_cost": 59},
        ],
    },
    {
        "name": "Enterprise",
        "description": "Every vector store, including AWS Bedrock KB, OpenSearch and neo4j.",
        "stacks": [
            {"stack": "pgvector", "monthly_cost": 0},
            {"stack": "chroma", "monthly_cost": 0},
            {"stack": "pinecone", "monthly_cost": 49},
            {"stack": "weaviate", "monthly_cost": 49},
            {"stack": "mongodb", "monthly_cost": 59},
            {"stack": "bedrock", "monthly_cost": 99},
            {"stack": "opensearch", "monthly_cost": 89},
            {"stack": "neo4j", "monthly_cost": 79},
        ],
    },
]


def seed(session: Session) -> None:
    _seed_admin(session)
    _seed_providers(session)
    _seed_subscription_plans(session)
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


def _seed_subscription_plans(session: Session) -> None:
    # Add any starter plan that isn't already present (matched by unique name), so
    # custom plans and edits to seeded ones survive restarts.
    existing_names = set(session.scalars(select(SubscriptionPlan.name)).all())
    for plan in DEFAULT_PLANS:
        if plan["name"] not in existing_names:
            session.add(SubscriptionPlan(**plan, status="active"))
