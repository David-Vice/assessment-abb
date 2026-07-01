import fakeredis.aioredis
import pytest
from abb_rag.rate_limit import allow_request, client_ip
from starlette.requests import Request


@pytest.mark.asyncio
async def test_allow_request_within_limit() -> None:
    redis = fakeredis.aioredis.FakeRedis()
    for _ in range(3):
        assert await allow_request(redis, scope="test", client_id="1.2.3.4", limit=3)


@pytest.mark.asyncio
async def test_allow_request_blocks_over_limit() -> None:
    redis = fakeredis.aioredis.FakeRedis()
    for _ in range(2):
        assert await allow_request(redis, scope="test", client_id="1.2.3.4", limit=2)
    assert not await allow_request(redis, scope="test", client_id="1.2.3.4", limit=2)


@pytest.mark.asyncio
async def test_allow_request_zero_limit_disables() -> None:
    redis = fakeredis.aioredis.FakeRedis()
    for _ in range(10):
        assert await allow_request(redis, scope="test", client_id="x", limit=0)


@pytest.mark.asyncio
async def test_allow_request_fail_closed_on_redis_error() -> None:
    class _BrokenRedis:
        def pipeline(self, transaction: bool = False) -> None:  # noqa: ARG002
            raise OSError("redis down")

    assert not await allow_request(
        _BrokenRedis(),  # type: ignore[arg-type]
        scope="test",
        client_id="1.2.3.4",
        limit=10,
        fail_open=False,
    )


@pytest.mark.asyncio
async def test_allow_request_fail_open_on_redis_error() -> None:
    class _BrokenRedis:
        def pipeline(self, transaction: bool = False) -> None:  # noqa: ARG002
            raise OSError("redis down")

    assert await allow_request(
        _BrokenRedis(),  # type: ignore[arg-type]
        scope="test",
        client_id="1.2.3.4",
        limit=10,
        fail_open=True,
    )


def test_client_ip_uses_socket_by_default() -> None:
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.1, 10.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)
    assert client_ip(request) == "127.0.0.1"


def test_client_ip_trusts_x_forwarded_for_when_enabled() -> None:
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.1, 10.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    request = Request(scope)
    assert client_ip(request, trust_proxy=True) == "203.0.113.1"
