import pytest
from abb_analytics.cache import cached
from abb_contracts import AnalyticsSummary

pytestmark = pytest.mark.asyncio

_SUMMARY = AnalyticsSummary(total_questions=5, answered_rate=0.8, avg_latency_ms=120.0)


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:  # noqa: ARG002
        self.store[key] = value


class _BrokenRedis:
    async def get(self, key: str) -> str | None:  # noqa: ARG002
        raise ConnectionError("redis down")

    async def set(self, key: str, value: str, ex: int) -> None:  # noqa: ARG002
        raise ConnectionError("redis down")


async def test_cache_miss_computes_and_stores(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = _FakeRedis()
    calls = 0

    async def producer() -> AnalyticsSummary:
        nonlocal calls
        calls += 1
        return _SUMMARY

    result = await cached(redis, "k", AnalyticsSummary, producer)  # type: ignore[arg-type]

    assert result == _SUMMARY
    assert calls == 1
    assert "analytics:k" in redis.store


async def test_cache_hit_skips_producer() -> None:
    redis = _FakeRedis()
    redis.store["analytics:k"] = _SUMMARY.model_dump_json()
    calls = 0

    async def producer() -> AnalyticsSummary:
        nonlocal calls
        calls += 1
        return _SUMMARY

    result = await cached(redis, "k", AnalyticsSummary, producer)  # type: ignore[arg-type]

    assert result == _SUMMARY
    assert calls == 0


async def test_cache_degrades_to_producer_when_redis_unavailable() -> None:
    async def producer() -> AnalyticsSummary:
        return _SUMMARY

    result = await cached(_BrokenRedis(), "k", AnalyticsSummary, producer)  # type: ignore[arg-type]

    assert result == _SUMMARY


async def test_cache_works_with_bare_list_types() -> None:
    redis = _FakeRedis()

    async def producer() -> list[int]:
        return [1, 2, 3]

    first = await cached(redis, "k", list[int], producer)  # type: ignore[arg-type]
    second = await cached(redis, "k", list[int], producer)  # type: ignore[arg-type] # cache hit

    assert first == [1, 2, 3]
    assert second == [1, 2, 3]


async def test_cache_none_redis_always_computes() -> None:
    calls = 0

    async def producer() -> AnalyticsSummary:
        nonlocal calls
        calls += 1
        return _SUMMARY

    await cached(None, "k", AnalyticsSummary, producer)
    await cached(None, "k", AnalyticsSummary, producer)

    assert calls == 2
