from collections.abc import Awaitable, Callable
from time import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from abb_rag import get_logger, get_settings

logger = get_logger(__name__)

_WINDOW_SECONDS = 60


def client_ip(request: Request) -> str:
    """Best-effort client identifier for per-IP rate limiting."""

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


async def allow_request(redis: object, *, scope: str, client_id: str, limit: int) -> bool:
    """Fixed-window counter: `limit` requests per minute per client."""

    if limit <= 0:
        return True

    bucket = int(time()) // _WINDOW_SECONDS
    key = f"ratelimit:{scope}:{client_id}:{bucket}"
    try:
        count = int(await redis.incr(key))  # type: ignore[attr-defined]
        if count == 1:
            await redis.expire(key, _WINDOW_SECONDS)  # type: ignore[attr-defined]
        return count <= limit
    except Exception as error:  # noqa: BLE001 — rate limit is best-effort
        logger.warning("rate_limit_check_failed", error=str(error))
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed per-IP rate limiting; skips `/health` and degrades if Redis is down."""

    def __init__(self, app: ASGIApp, *, scope: str) -> None:
        super().__init__(app)
        self._scope = scope

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        redis: object | None = getattr(request.app.state, "redis", None)
        if redis is None:
            return await call_next(request)

        limit = get_settings().rate_limit_per_minute
        if not await allow_request(
            redis, scope=self._scope, client_id=client_ip(request), limit=limit
        ):
            return JSONResponse(
                status_code=429,
                content={
                    "code": "RATE_LIMITED",
                    "detail": "Too many requests. Please try again shortly.",
                },
            )

        return await call_next(request)
