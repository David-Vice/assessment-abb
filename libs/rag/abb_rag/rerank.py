import asyncio
from dataclasses import replace
from functools import lru_cache
from typing import Any

from abb_rag.exceptions import ExternalServiceError
from abb_rag.log import get_logger
from abb_rag.models import RetrievedChunk
from abb_rag.settings import get_settings

logger = get_logger(__name__)


@lru_cache
def _load_model() -> Any:
    # Lazy: sentence-transformers pulls torch (the heaviest dep); with
    # RERANK_ENABLED=false it is never imported. Returned as Any — its CrossEncoder
    # typing is environment-dependent and the predict() stub is over-narrow.
    from sentence_transformers import CrossEncoder

    settings = get_settings()
    logger.info("rerank_model_loading", model=settings.rerank_model)
    return CrossEncoder(settings.rerank_model)


def _score(query: str, candidates: list[RetrievedChunk]) -> list[float]:
    model = _load_model()
    pairs = [(query, candidate.content) for candidate in candidates]
    return [float(score) for score in model.predict(pairs)]


async def rerank(query: str, candidates: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    """Re-score hybrid candidates with a cross-encoder; keep the top-k.

    The cross-encoder is CPU-bound, so it runs off the event loop via a thread
    (model load happens lazily inside that thread on first use).
    """

    if not candidates:
        return []
    try:
        scores = await asyncio.to_thread(_score, query, candidates)
    except Exception as error:
        raise ExternalServiceError(f"rerank failed: {error}") from error
    ranked = sorted(
        zip(candidates, scores, strict=True),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return [replace(candidate, score=score) for candidate, score in ranked[:top_k]]
