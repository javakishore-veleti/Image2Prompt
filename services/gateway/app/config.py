from __future__ import annotations

from image2prompt_shared.settings import ServiceSettings


class GatewaySettings(ServiceSettings):
    service_name: str = "gateway"
    # Fixed-window rate limit per client (subject if authenticated, else IP).
    rate_limit_enabled: bool = True
    rate_limit_rpm: int = 120
    # Tighter per-IP budget for unauthenticated auth endpoints (login / signup /
    # password reset) to blunt credential-stuffing. Failures are already audited.
    auth_rate_limit_rpm: int = 10
    # Rate-limit window store: "memory" (per-replica) or "redis" (shared across
    # replicas). Redis failures degrade gracefully back to in-memory counting.
    ratelimit_backend: str = "memory"
    redis_url: str = "redis://localhost:6379/0"
    # Security response headers + max request body (bytes; 0 disables the cap).
    security_headers_enabled: bool = True
    hsts_enabled: bool = False  # enable once served over HTTPS
    max_body_bytes: int = 15_000_000  # ~15 MB (image uploads)


settings = GatewaySettings()
