import contextlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from abb_analytics import queries
from abb_contracts import Language, Segment

FROM = datetime(2026, 1, 1, tzinfo=UTC)
TO = datetime(2026, 2, 1, tzinfo=UTC)


class _FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def one(self) -> Any:
        return self._rows[0]

    def all(self) -> list[Any]:
        return self._rows


class _FakeSession:
    """Returns queued result sets in order; records params for assertions."""

    def __init__(self, result_sets: list[list[Any]]) -> None:
        self._results = result_sets
        self._index = 0
        self.calls: list[dict[str, Any]] = []

    async def execute(self, _sql: Any, params: dict[str, Any]) -> _FakeResult:
        self.calls.append(params)
        rows = self._results[self._index]
        self._index += 1
        return _FakeResult(rows)


def _patch(monkeypatch: pytest.MonkeyPatch, session: _FakeSession) -> None:
    @contextlib.asynccontextmanager
    async def _scope() -> AsyncIterator[_FakeSession]:
        yield session

    monkeypatch.setattr(queries, "session_scope", _scope)


@pytest.mark.asyncio
async def test_summary_computes_answered_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    session = _FakeSession([[SimpleNamespace(total=10, answered=7, avg_latency=123.0)]])
    _patch(monkeypatch, session)

    # Act
    result = await queries.get_summary(FROM, TO, None)

    # Assert
    assert result.total_questions == 10
    assert result.answered_rate == 0.7
    assert result.avg_latency_ms == 123.0


@pytest.mark.asyncio
async def test_summary_zero_total_avoids_division(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    session = _FakeSession([[SimpleNamespace(total=0, answered=0, avg_latency=0)]])
    _patch(monkeypatch, session)

    # Act
    result = await queries.get_summary(FROM, TO, None)

    # Assert
    assert result.answered_rate == 0.0


@pytest.mark.asyncio
async def test_performance_estimates_cost_from_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange — 1M prompt + 1M completion → $2.50 + $10.00.
    session = _FakeSession(
        [
            [
                SimpleNamespace(
                    avg_latency=100.0,
                    p95_latency=200.0,
                    avg_tokens=500.0,
                    sum_prompt=1_000_000,
                    sum_completion=1_000_000,
                )
            ]
        ]
    )
    _patch(monkeypatch, session)

    # Act
    result = await queries.get_performance(FROM, TO, None)

    # Assert
    assert result.p95_latency_ms == 200.0
    assert result.estimated_cost_usd == 12.50


@pytest.mark.asyncio
async def test_quality_fills_missing_statuses_with_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange — only two statuses present; the rest must default to 0.
    session = _FakeSession(
        [
            [
                SimpleNamespace(status="answered", n=8),
                SimpleNamespace(status="declined_injection", n=2),
            ]
        ]
    )
    _patch(monkeypatch, session)

    # Act
    result = await queries.get_quality(FROM, TO, None)

    # Assert
    assert result.answered == 8
    assert result.declined_injection == 2
    assert result.declined_off_topic == 0
    assert result.error == 0


@pytest.mark.asyncio
async def test_distribution_maps_language_and_skips_null_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange — lang rows, then segment rows (one with a NULL segment to drop).
    session = _FakeSession(
        [
            [SimpleNamespace(language="az", n=5), SimpleNamespace(language="en", n=3)],
            [
                SimpleNamespace(segment="individuals", n=4),
                SimpleNamespace(segment=None, n=9),
            ],
        ]
    )
    _patch(monkeypatch, session)

    # Act
    result = await queries.get_distribution(FROM, TO, None)

    # Assert
    assert result.by_language == {Language.AZ: 5, Language.EN: 3}
    assert result.by_segment == {Segment.INDIVIDUALS: 4}


@pytest.mark.asyncio
async def test_volume_invalid_bucket_falls_back_to_day(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    session = _FakeSession([[SimpleNamespace(bucket=FROM, n=3)]])
    _patch(monkeypatch, session)

    # Act
    result = await queries.get_volume(FROM, TO, "weekly", None)

    # Assert
    assert session.calls[0]["bucket"] == "day"
    assert result.points[0].count == 3


@pytest.mark.asyncio
async def test_top_questions_maps_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    session = _FakeSession(
        [[SimpleNamespace(question="What is ABB?", n=12), SimpleNamespace(question="Cards?", n=4)]]
    )
    _patch(monkeypatch, session)

    # Act
    result = await queries.get_top_questions(FROM, TO, 10, None)

    # Assert
    assert [q.question for q in result] == ["What is ABB?", "Cards?"]
    assert result[0].count == 12


@pytest.mark.asyncio
async def test_language_filter_passes_through_to_params(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    session = _FakeSession([[SimpleNamespace(total=1, answered=1, avg_latency=10.0)]])
    _patch(monkeypatch, session)

    # Act
    await queries.get_summary(FROM, TO, Language.RU)

    # Assert
    assert session.calls[0]["lang"] == "ru"
