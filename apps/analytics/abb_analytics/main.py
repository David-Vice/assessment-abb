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
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "detail": exc.message},
        )

    app.include_router(analytics_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    return app


app = create_app()
