from collections.abc import Awaitable, Callable

from abb_rag import get_logger
from pydantic import BaseModel
from redis.asyncio import Redis

logger = get_logger(__name__)

CACHE_TTL_SECONDS = 60
CACHE_PREFIX = "analytics:"


async def cached[T: BaseModel](
    redis: Redis | None,
    key: str,
    model_cls: type[T],
    producer: Callable[[], Awaitable[T]],
) -> T:
    """Return a cached aggregation or compute + store it (60s TTL).

    Caching is best-effort: any Redis failure falls back to a direct DB query so
    the dashboard never breaks because the cache is unavailable.
    """

    full_key = f"{CACHE_PREFIX}{key}"
    if redis is not None:
        try:
            raw = await redis.get(full_key)
            if raw is not None:
                return model_cls.model_validate_json(raw)
        except Exception as error:  # noqa: BLE001 — cache is non-critical
            logger.warning("analytics_cache_read_failed", error=str(error))

    value = await producer()

    if redis is not None:
        try:
            await redis.set(full_key, value.model_dump_json(), ex=CACHE_TTL_SECONDS)
        except Exception as error:  # noqa: BLE001 — cache is non-critical
            logger.warning("analytics_cache_write_failed", error=str(error))

    return value
