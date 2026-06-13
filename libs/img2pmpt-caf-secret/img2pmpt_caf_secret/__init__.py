"""img2pmpt-caf-secret — Common Application Framework: secrets.

Microservices use the ``client`` sub-package (``ISecretClient`` /
``SecretClient``) to fetch secrets via ``get_secret_by_key`` /
``get_secrets_by_keys`` and stay agnostic to the underlying provider. The active
provider (env / aws / azure / gcp) is chosen by feature toggle at deploy time and
implemented in the ``provider_impls`` sub-package.
"""

from .client.dtos import (
    GetSecretReq,
    GetSecretResp,
    GetSecretsReq,
    GetSecretsResp,
)
from .client.interfaces import ISecretClient
from .client.secret_client import SecretClient, get_secret_client

__version__ = "0.1.0"

__all__ = [
    "ISecretClient",
    "SecretClient",
    "get_secret_client",
    "GetSecretReq",
    "GetSecretResp",
    "GetSecretsReq",
    "GetSecretsResp",
]
