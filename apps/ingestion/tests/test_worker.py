from datetime import UTC, datetime
from typing import Any

import fakeredis.aioredis
import pytest
from abb_contracts import Corpus, CorpusDocument, IngestionState, Language, Segment
from abb_ingestion import worker as worker_module
from abb_ingestion.progress import init_progress, read_status
from abb_ingestion.worker import ingest_corpus_job


def _corpus_payload() -> dict[str, Any]:
    document = CorpusDocument(
        url="https://abb-bank.az/x",
        language=Language.EN,
        segment=Segment.OTHER,
        title="T",
        markdown="A sufficiently long body to index.",
        content_hash="sha256:x",
        fetched_at=datetime.now(UTC),
    )
    corpus = Corpus(source="abb-bank.az", generated_at=datetime.now(UTC), documents=[document])
    return corpus.model_dump(mode="json")


async def test_ingest_corpus_job_completes_and_tracks_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange — the router sets the full-corpus total before enqueue; the worker
    # only advances `processed`, so seed total here to mirror that lifecycle.
    redis = fakeredis.aioredis.FakeRedis()
    ctx = {"job_id": "job-9", "redis": redis}
    await init_progress(redis, "job-9", total=1)

    async def fake_ingest(corpus: Any, on_progress: Any = None) -> int:
        if on_progress is not None:
            await on_progress(1, 1)
        return 4

    monkeypatch.setattr(worker_module, "ingest_corpus", fake_ingest)

    # Act
    indexed = await ingest_corpus_job(ctx, _corpus_payload())

    # Assert
    assert indexed == 4
    status = await read_status(redis, "job-9")
    assert status is not None
    assert status.state is IngestionState.COMPLETED
    assert status.processed == 1
    assert status.total == 1


async def test_ingest_corpus_job_marks_failed_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    redis = fakeredis.aioredis.FakeRedis()
    ctx = {"job_id": "job-x", "redis": redis}

    async def fake_ingest(corpus: Any, on_progress: Any = None) -> int:
        raise RuntimeError("boom")

    monkeypatch.setattr(worker_module, "ingest_corpus", fake_ingest)

    # Act & Assert
    with pytest.raises(RuntimeError):
        await ingest_corpus_job(ctx, _corpus_payload())
    status = await read_status(redis, "job-x")
    assert status is not None
    assert status.state is IngestionState.FAILED
