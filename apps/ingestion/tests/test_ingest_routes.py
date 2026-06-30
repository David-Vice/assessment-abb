from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import abb_ingestion.main as main_module
import fakeredis.aioredis
import pytest
from abb_contracts import Corpus, CorpusDocument, Language, Segment
from abb_ingestion.main import create_app
from fastapi.testclient import TestClient


class _FakeArqRedis(fakeredis.aioredis.FakeRedis):
    async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(job_id="job-test-1")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    fake = _FakeArqRedis()

    async def fake_pool() -> _FakeArqRedis:
        return fake

    monkeypatch.setattr(main_module, "create_redis_pool", fake_pool)
    with TestClient(create_app()) as test_client:
        yield test_client


def _payload() -> dict[str, Any]:
    document = CorpusDocument(
        url="https://abb-bank.az/x",
        language=Language.EN,
        segment=Segment.OTHER,
        title="T",
        markdown="A body to ingest.",
        content_hash="sha256:x",
        fetched_at=datetime.now(UTC),
    )
    corpus = Corpus(source="abb-bank.az", generated_at=datetime.now(UTC), documents=[document])
    return {"corpus": corpus.model_dump(mode="json")}


def test_create_ingestion_enqueues_and_reports_queued(client: TestClient) -> None:
    # Act
    response = client.post("/ingest", json=_payload())

    # Assert
    assert response.status_code == 200
    job = response.json()
    assert job["state"] == "queued"

    status = client.get(f"/ingest/{job['job_id']}")
    assert status.status_code == 200
    body = status.json()
    assert body["state"] == "queued"
    assert body["total"] == 1


def test_get_unknown_job_returns_404(client: TestClient) -> None:
    # Act
    response = client.get("/ingest/does-not-exist")

    # Assert
    assert response.status_code == 404


def test_rate_limit_returns_429(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from abb_rag.settings import get_settings

    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    get_settings.cache_clear()

    first = client.post("/ingest", json=_payload())
    second = client.post("/ingest", json=_payload())

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == "RATE_LIMITED"

    # GET polling is not counted — still allowed after POST limit is hit.
    status = client.get(f"/ingest/{first.json()['job_id']}")
    assert status.status_code == 200
