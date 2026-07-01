from collections.abc import Awaitable, Callable
from time import time

from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from abb_rag import get_logger, get_settings
from abb_rag.exceptions import RateLimitError

logger = get_logger(__name__)

_WINDOW_SECONDS = 60


def client_ip(request: Request, *, trust_proxy: bool = False) -> str:
    """Client identifier for per-IP rate limiting.

    By default uses the TCP peer address only. Enable ``trust_proxy`` only when
    Uvicorn runs with ``--proxy-headers`` and a configured ``forwarded-allow-ips``.
    """

    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


async def allow_request(
    redis: Redis,
    *,
    scope: str,
    client_id: str,
    limit: int,
    fail_open: bool = False,
) -> bool:
    """Fixed-window counter: ``limit`` requests per minute per client."""

    if limit <= 0:
        return True

    bucket = int(time()) // _WINDOW_SECONDS
    key = f"ratelimit:{scope}:{client_id}:{bucket}"
    try:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, _WINDOW_SECONDS)
            count, _ = await pipe.execute()
        return int(count) <= limit
    except Exception as error:  # noqa: BLE001 — degrade per settings
        logger.warning("rate_limit_check_failed", error=str(error))
        return fail_open


def rate_limited_response() -> JSONResponse:
    exc = RateLimitError()
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "detail": exc.message},
    )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed per-IP rate limiting on expensive POSTs only.

    Skips ``/health`` and all GETs (ingestion status polling, session hydration).
    When Redis is unavailable at startup, requests pass through unthrottled.
    """

    def __init__(self, app: ASGIApp, *, scope: str) -> None:
        super().__init__(app)
        self._scope = scope

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path == "/health" or request.method != "POST":
            return await call_next(request)

        redis: Redis | None = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        settings = get_settings()
        if not await allow_request(
            redis,
            scope=self._scope,
            client_id=client_ip(request, trust_proxy=settings.rate_limit_trust_proxy),
            limit=settings.rate_limit_per_minute,
            fail_open=settings.rate_limit_fail_open,
        ):
            return rate_limited_response()

        return await call_next(request)
