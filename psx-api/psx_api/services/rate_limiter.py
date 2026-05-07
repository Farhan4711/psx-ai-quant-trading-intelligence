"""
Redis-backed rate limiter for login attempts.
Key: rate_limit:login:{ip}  →  attempt count (TTL 3600s)
Max 5 failed attempts per IP per hour before locking out.
"""

from __future__ import annotations

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 3600
_KEY_PREFIX = "rate_limit:login:"


class LoginRateLimiter:
    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    def _key(self, ip: str) -> str:
        return f"{_KEY_PREFIX}{ip}"

    async def is_blocked(self, ip: str) -> bool:
        count_raw = await self._redis.get(self._key(ip))
        if count_raw is None:
            return False
        return int(count_raw) >= _MAX_ATTEMPTS

    async def record_failure(self, ip: str) -> int:
        """Increments failure count; returns current count."""
        key = self._key(ip)
        count = await self._redis.incr(key)
        if count == 1:
            # First failure — set expiry window
            await self._redis.expire(key, _WINDOW_SECONDS)
        logger.warning("Login failure recorded", ip=ip, count=count, max=_MAX_ATTEMPTS)
        return int(count)

    async def clear(self, ip: str) -> None:
        """Clears failure count on successful login."""
        await self._redis.delete(self._key(ip))
