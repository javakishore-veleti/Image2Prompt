"""Pluggable fixed-window rate limiter for the gateway.

Two backends, selected by ``RATELIMIT_BACKEND``:
- ``memory``: per-replica in-process counters (default; fine for a single gateway).
- ``redis``: a shared counter so the limit holds across multiple gateway replicas.

Fail-safe, in the CAF spirit: if the redis package is missing or the server is
unreachable, the limiter degrades to in-memory counting (logged once) rather than
raising or letting unlimited traffic through. The window is fixed at 60 seconds.
"""

from __future__ import annotations

import time

from image2prompt_shared.logging_config import get_logger

log = get_logger(__name__)

_WINDOW_SECONDS = 60


class RateLimiter:
    async def over_limit(self, key: str, limit: int) -> bool:  # pragma: no cover - interface
        raise NotImplementedError


class MemoryRateLimiter(RateLimiter):
    """In-process fixed-window counter. Not shared across replicas."""

    def __init__(self) -> None:
        self._windows: dict[tuple[str, int], int] = {}

    async def over_limit(self, key: str, limit: int) -> bool:
        if limit <= 0:
            return False
        window = int(time.time() // _WINDOW_SECONDS)
        bucket = (key, window)
        self._windows[bucket] = self._windows.get(bucket, 0) + 1
        if len(self._windows) > 10000:  # opportunistic cleanup of old windows
            for k in [k for k in self._windows if k[1] != window]:
                self._windows.pop(k, None)
        return self._windows[bucket] > limit


class RedisRateLimiter(RateLimiter):
    """Shared fixed-window counter in Redis (atomic INCR + EXPIRE). Degrades to an
    in-memory limiter if Redis is missing/unreachable."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client = None
        self._init_failed = False
        self._fallback = MemoryRateLimiter()
        self._degraded_logged = False

    async def _get_client(self):
        if self._client is None and not self._init_failed:
            try:
                import redis.asyncio as redis  # lazy: only needed for this backend

                self._client = redis.from_url(
                    self._url, socket_connect_timeout=2, socket_timeout=2, decode_responses=True
                )
            except Exception as exc:  # package missing / bad url
                self._init_failed = True
                log.warning("redis rate-limiter unavailable (%s); using in-memory", exc)
        return self._client

    def _degrade(self, exc: Exception):
        if not self._degraded_logged:
            log.warning("redis rate-limiter error (%s); degrading to in-memory", exc)
            self._degraded_logged = True

    async def over_limit(self, key: str, limit: int) -> bool:
        if limit <= 0:
            return False
        client = await self._get_client()
        if client is None:
            return await self._fallback.over_limit(key, limit)
        window = int(time.time() // _WINDOW_SECONDS)
        rkey = f"rl:{key}:{window}"
        try:
            count = await client.incr(rkey)
            if count == 1:
                await client.expire(rkey, _WINDOW_SECONDS * 2)
            return count > limit
        except Exception as exc:  # Redis went away mid-flight
            self._degrade(exc)
            return await self._fallback.over_limit(key, limit)


def build_rate_limiter(settings) -> RateLimiter:
    backend = (getattr(settings, "ratelimit_backend", "memory") or "memory").lower()
    if backend == "redis":
        log.info("rate limiter backend: redis (%s)", settings.redis_url)
        return RedisRateLimiter(settings.redis_url)
    return MemoryRateLimiter()
