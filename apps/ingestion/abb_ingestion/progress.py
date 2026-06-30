from abb_contracts import IngestionState, IngestionStatus
from redis.asyncio import Redis

# Job progress is tracked in a Redis hash (the FastAPI side reads it; the worker
# writes it). arq tracks queued/running internally, but we own processed/total.
#
# redis-py types its commands as `Awaitable[T] | T` (one signature for the sync
# and async clients), so awaiting them needs a narrow `type: ignore[misc]`.
PROGRESS_PREFIX = "ingest:progress:"
PROGRESS_TTL_SECONDS = 86_400
_ERROR_MAX_CHARS = 500


def _key(job_id: str) -> str:
    return f"{PROGRESS_PREFIX}{job_id}"


async def init_progress(redis: Redis, job_id: str, total: int) -> None:
    await redis.hset(  # type: ignore[misc]
        _key(job_id),
        mapping={"state": IngestionState.QUEUED.value, "processed": 0, "total": total, "error": ""},
    )
    await redis.expire(_key(job_id), PROGRESS_TTL_SECONDS)


async def set_state(redis: Redis, job_id: str, state: IngestionState) -> None:
    # Clear any prior error so a successful (re)run never surfaces stale failure text.
    await redis.hset(_key(job_id), mapping={"state": state.value, "error": ""})  # type: ignore[misc]


async def set_processed(redis: Redis, job_id: str, processed: int, total: int) -> None:
    await redis.hset(_key(job_id), mapping={"processed": processed, "total": total})  # type: ignore[misc]


async def set_failed(redis: Redis, job_id: str, error: str) -> None:
    await redis.hset(  # type: ignore[misc]
        _key(job_id),
        mapping={"state": IngestionState.FAILED.value, "error": error[:_ERROR_MAX_CHARS]},
    )


async def read_status(redis: Redis, job_id: str) -> IngestionStatus | None:
    raw = await redis.hgetall(_key(job_id))  # type: ignore[misc]
    if not raw:
        return None
    data = {_text(key): _text(value) for key, value in raw.items()}
    return IngestionStatus(
        job_id=job_id,
        state=IngestionState(data["state"]),
        processed=int(data.get("processed", 0)),
        total=int(data.get("total", 0)),
        error=data.get("error") or None,
    )


def _text(value: object) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)
