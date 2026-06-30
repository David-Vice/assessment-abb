import fakeredis.aioredis
from abb_contracts import IngestionState
from abb_ingestion.progress import (
    init_progress,
    read_status,
    set_failed,
    set_processed,
    set_state,
)


async def test_progress_roundtrip_tracks_state_and_counts() -> None:
    # Arrange
    redis = fakeredis.aioredis.FakeRedis()
    await init_progress(redis, "job-1", total=10)

    # Act & Assert — queued after init
    status = await read_status(redis, "job-1")
    assert status is not None
    assert status.state is IngestionState.QUEUED
    assert status.total == 10
    assert status.processed == 0

    # Act & Assert — running with progress; total stays fixed from init_progress
    await set_state(redis, "job-1", IngestionState.RUNNING)
    await set_processed(redis, "job-1", 5)
    status = await read_status(redis, "job-1")
    assert status is not None
    assert status.state is IngestionState.RUNNING
    assert status.processed == 5
    assert status.total == 10

    # Act & Assert — failure carries the error
    await set_failed(redis, "job-1", "boom")
    status = await read_status(redis, "job-1")
    assert status is not None
    assert status.state is IngestionState.FAILED
    assert status.error == "boom"


async def test_read_status_missing_job_returns_none() -> None:
    # Arrange
    redis = fakeredis.aioredis.FakeRedis()

    # Act & Assert
    assert await read_status(redis, "unknown") is None
