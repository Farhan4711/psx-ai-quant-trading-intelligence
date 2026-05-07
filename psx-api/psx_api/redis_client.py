from collections.abc import AsyncGenerator

from redis.asyncio import Redis, from_url

from psx_api.config import settings

_redis_pool: Redis | None = None  # type: ignore[type-arg]


def get_redis_pool() -> Redis:  # type: ignore[type-arg]
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = from_url(settings.redis_url, decode_responses=True)
    return _redis_pool


async def get_redis() -> AsyncGenerator[Redis, None]:  # type: ignore[type-arg]
    redis = get_redis_pool()
    try:
        yield redis
    finally:
        pass  # Pool connection — do not close per-request


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
