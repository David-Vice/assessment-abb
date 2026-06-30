from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from abb_rag import AppError, configure_logging, get_logger, get_settings
from abb_rag.rate_limit import RateLimitMiddleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from abb_chat.routers.chat import router as chat_router

SERVICE_NAME = "chat"
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    # Rate limiting is best-effort: if Redis is unreachable, requests pass through
    # (see RateLimitMiddleware) so chat never breaks because Redis is down.
    try:
        app.state.redis = Redis.from_url(get_settings().redis_url)
    except Exception as error:  # noqa: BLE001
        logger.warning("chat_redis_unavailable", error=str(error))
        app.state.redis = None
    try:
        yield
    finally:
        if app.state.redis is not None:
            await app.state.redis.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ABB RAG — Chat Service", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, scope="chat")

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "detail": exc.message},
        )

    app.include_router(chat_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    return app


app = create_app()
