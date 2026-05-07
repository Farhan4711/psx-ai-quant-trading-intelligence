"""
Redis cache utility with TTL tiers.

TTL policy (per build-plan Step 18):
  - 1 min   : live prices / indices (market hours)
  - 5 min   : securities list / detail / announcements
  - 1 hour  : OHLCV / fundamentals
  - 24 hours: sector list
"""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine

from redis.asyncio import Redis

TTL_LIVE = 60          # 1 min
TTL_LIST = 300         # 5 min
TTL_OHLCV = 3600       # 1 hour
TTL_FUNDAMENTALS = 3600
TTL_SECTORS = 86400    # 24 hours


async def cache_get(redis: Redis, key: str) -> Any | None:  # type: ignore[type-arg]
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def cache_set(redis: Redis, key: str, value: Any, ttl: int) -> None:  # type: ignore[type-arg]
    await redis.setex(key, ttl, json.dumps(value, default=str))


async def cached(
    redis: Redis,  # type: ignore[type-arg]
    key: str,
    ttl: int,
    loader: Callable[[], Coroutine[Any, Any, Any]],
) -> Any:
    """
    Returns cached value if present; otherwise calls loader(), caches, and returns it.
    loader must return a JSON-serialisable value (dict / list / primitive).
    """
    hit = await cache_get(redis, key)
    if hit is not None:
        return hit
    value = await loader()
    if value is not None:
        await cache_set(redis, key, value, ttl)
    return value


def invalidate_securities_cache(redis: Redis, symbol: str | None = None) -> Coroutine[Any, Any, None]:  # type: ignore[type-arg]
    """Call after any securities mutation to bust stale cache entries."""
    if symbol:
        return redis.delete(f"sec:{symbol}", f"ohlcv:{symbol}", f"fundamentals:{symbol}", f"announcements:{symbol}")
    return redis.delete("sectors", "indices")
