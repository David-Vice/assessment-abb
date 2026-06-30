from typing import Any

from abb_contracts import Corpus, IngestionState
from abb_rag import configure_logging, get_logger, ingest_corpus

from abb_ingestion.progress import set_failed, set_processed, set_state
from abb_ingestion.redis_pool import get_redis_settings

logger = get_logger(__name__)

INGEST_TASK = "ingest_corpus_job"


async def ingest_corpus_job(ctx: dict[str, Any], corpus_data: dict[str, Any]) -> int:
    """arq task: index an uploaded corpus, streaming progress to Redis."""

    job_id: str = ctx["job_id"]
    redis = ctx["redis"]
    corpus = Corpus.model_validate(corpus_data)
    logger.info("ingest_job_started", job_id=job_id, documents=len(corpus.documents))
    await set_state(redis, job_id, IngestionState.RUNNING)

    async def on_progress(done: int, _total: int) -> None:
        await set_processed(redis, job_id, done)

    try:
        indexed = await ingest_corpus(corpus, on_progress=on_progress)
    except Exception as error:
        await set_failed(redis, job_id, str(error))
        logger.error("ingest_job_failed", job_id=job_id, error=str(error))
        raise

    await set_state(redis, job_id, IngestionState.COMPLETED)
    logger.info("ingest_job_completed", job_id=job_id, chunks=indexed)
    return indexed


async def _on_startup(_: dict[str, Any]) -> None:
    configure_logging()


class WorkerSettings:
    """arq worker entrypoint: `arq abb_ingestion.worker.WorkerSettings`."""

    functions = [ingest_corpus_job]
    redis_settings = get_redis_settings()
    on_startup = _on_startup
