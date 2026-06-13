"""Provider implementations + factory. Microservices never import these directly
— the SecretClient resolves the active one from config."""

from .interfaces import ISecretProvider
from .factory import build_provider

__all__ = ["ISecretProvider", "build_provider"]
