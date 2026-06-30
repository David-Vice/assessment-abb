from datetime import UTC, datetime

import pytest
from abb_analytics import queries
from abb_analytics.routers.analytics import router
from abb_contracts import TimeBucket, VolumeSeries
from fastapi import FastAPI
from fastapi.testclient import TestClient

FROM = datetime(2026, 1, 1, tzinfo=UTC)
TO = datetime(2026, 2, 1, tzinfo=UTC)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A bare app with the analytics router, no real DB/Redis (cache disabled)."""

    async def fake_get_volume(*_args: object, **_kwargs: object) -> VolumeSeries:
        return VolumeSeries(points=[TimeBucket(bucket=FROM, count=1)])

    monkeypatch.setattr(queries, "get_volume", fake_get_volume)

    app = FastAPI()
    app.include_router(router)
    app.state.redis = None
    return TestClient(app)


def test_volume_rejects_invalid_bucket_with_422(client: TestClient) -> None:
    params = {"from": FROM.isoformat(), "to": TO.isoformat(), "bucket": "weekly"}
    response = client.get("/analytics/volume", params=params)
    assert response.status_code == 422


def test_volume_accepts_valid_bucket(client: TestClient) -> None:
    params = {"from": FROM.isoformat(), "to": TO.isoformat(), "bucket": "hour"}
    response = client.get("/analytics/volume", params=params)
    assert response.status_code == 200
    assert response.json()["points"][0]["count"] == 1
