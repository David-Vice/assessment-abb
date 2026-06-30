from abb_contracts import IngestionJob, IngestionRequest, IngestionState, IngestionStatus
from abb_rag import ExternalServiceError, NotFoundError, get_logger
from fastapi import APIRouter, Request

from abb_ingestion.progress import init_progress, read_status
from abb_ingestion.worker import INGEST_TASK

logger = get_logger(__name__)
router = APIRouter(tags=["ingestion"])


@router.post("/ingest", response_model=IngestionJob)
async def create_ingestion(request: Request, body: IngestionRequest) -> IngestionJob:
    """Validate the uploaded corpus and enqueue an async indexing job."""

    redis = request.app.state.redis
    job = await redis.enqueue_job(INGEST_TASK, body.corpus.model_dump(mode="json"))
    if job is None:
        raise ExternalServiceError("could not enqueue ingestion job")
    await init_progress(redis, job.job_id, total=len(body.corpus.documents))
    logger.info("ingest_enqueued", job_id=job.job_id, documents=len(body.corpus.documents))
    return IngestionJob(job_id=job.job_id, state=IngestionState.QUEUED)


@router.get("/ingest/{job_id}", response_model=IngestionStatus)
async def get_ingestion_status(request: Request, job_id: str) -> IngestionStatus:
    status = await read_status(request.app.state.redis, job_id)
    if status is None:
        raise NotFoundError(f"ingestion job not found: {job_id}")
    return status
