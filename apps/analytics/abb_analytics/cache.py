from collections.abc import Awaitable, Callable

from abb_rag import get_logger
from pydantic import TypeAdapter
from redis.asyncio import Redis

logger = get_logger(__name__)

CACHE_TTL_SECONDS = 60
CACHE_PREFIX = "analytics:"


async def cached[T](
    redis: Redis | None,
    key: str,
    type_: type[T],
    producer: Callable[[], Awaitable[T]],
) -> T:
    """Return a cached aggregation or compute + store it (60s TTL).

    `type_` may be a Pydantic model or any other `TypeAdapter`-serializable type
    (e.g. `list[TopQuestion]`), so endpoints returning a bare list can cache too.
    Caching is best-effort: any Redis failure falls back to a direct DB query so
    the dashboard never breaks because the cache is unavailable.
    """

    adapter = TypeAdapter(type_)
    full_key = f"{CACHE_PREFIX}{key}"
    if redis is not None:
        try:
            raw = await redis.get(full_key)
            if raw is not None:
                return adapter.validate_json(raw)
        except Exception as error:  # noqa: BLE001 — cache is non-critical
            logger.warning("analytics_cache_read_failed", error=str(error))

    value = await producer()

    if redis is not None:
        try:
            await redis.set(full_key, adapter.dump_json(value), ex=CACHE_TTL_SECONDS)
        except Exception as error:  # noqa: BLE001 — cache is non-critical
            logger.warning("analytics_cache_write_failed", error=str(error))

    return value
