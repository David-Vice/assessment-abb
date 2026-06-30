from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from abb_rag import AppError, configure_logging, get_logger, get_settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from abb_analytics.routers.analytics import router as analytics_router

SERVICE_NAME = "analytics"
logger = get_logger(__name__)

# Safe, generic client-facing messages — raw upstream/SQL detail stays in logs
# only (same pattern as the chat service's _PUBLIC_DETAIL).
_PUBLIC_DETAIL = {
    "UPSTREAM_ERROR": "A required service is temporarily unavailable. Please try again.",
    "VALIDATION_ERROR": "The request was invalid.",
    "NOT_FOUND": "The requested resource was not found.",
    "INTERNAL_ERROR": "Something went wrong. Please try again.",
}


def _public_detail(code: str) -> str:
    return _PUBLIC_DETAIL.get(code, _PUBLIC_DETAIL["INTERNAL_ERROR"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    # Cache is best-effort: if Redis is unreachable, endpoints fall back to direct
    # DB queries (see cache.cached), so a connection failure must not crash startup.
    try:
        app.state.redis = Redis.from_url(get_settings().redis_url)
    except Exception as error:  # noqa: BLE001
        logger.warning("analytics_redis_unavailable", error=str(error))
        app.state.redis = None
    try:
        yield
    finally:
        if app.state.redis is not None:
            await app.state.redis.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ABB RAG — Analytics Service", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.error("analytics_app_error", code=exc.code, detail=exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "detail": _public_detail(exc.code)},
        )

    app.include_router(analytics_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    return app


app = create_app()
