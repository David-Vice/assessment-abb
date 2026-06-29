from collections.abc import Callable

from abb_contracts import Corpus, CorpusDocument, Language
from sqlalchemy.ext.asyncio import AsyncSession

from abb_rag.chunking import chunk_document
from abb_rag.db import session_scope
from abb_rag.dedup import dedup_chunks, find_boilerplate
from abb_rag.embeddings import embed_texts
from abb_rag.log import get_logger
from abb_rag.models import Chunk, RetrievedChunk
from abb_rag.retriever import hybrid_search
from abb_rag.settings import get_settings
from abb_rag.vectorstore import load_existing_hashes, upsert_document

logger = get_logger(__name__)

ProgressCallback = Callable[[int, int], None]


async def ingest_corpus(corpus: Corpus, on_progress: ProgressCallback | None = None) -> int:
    """Chunk → dedup → embed → upsert. Idempotent: unchanged docs are skipped.

    Owns its transactions: hashes are read in a short transaction, embedding runs
    outside any transaction (no idle-in-transaction across OpenAI I/O), and each
    document is written in its own transaction so progress is durable on failure.
    Returns the number of chunks indexed in this run.
    """

    chunked = [(document, chunk_document(document)) for document in corpus.documents]
    boilerplate = find_boilerplate([chunks for _, chunks in chunked])

    async with session_scope() as session:
        existing = await load_existing_hashes(session)

    pending: list[tuple[CorpusDocument, list[Chunk]]] = [
        (document, dedup_chunks(chunks, boilerplate))
        for document, chunks in chunked
        if existing.get(document.url) != document.content_hash
    ]
    if not pending:
        logger.info("ingest_skipped_all_unchanged", documents=len(chunked))
        return 0

    all_chunks = [chunk for _, chunks in pending for chunk in chunks]
    logger.info(
        "ingest_embedding",
        documents=len(pending),
        chunks=len(all_chunks),
        boilerplate_dropped=len(boilerplate),
    )
    vectors = await embed_texts([chunk.content for chunk in all_chunks])

    indexed = 0
    cursor = 0
    for done, (document, chunks) in enumerate(pending, start=1):
        doc_vectors = vectors[cursor : cursor + len(chunks)]
        cursor += len(chunks)
        async with session_scope() as session:
            await upsert_document(session, document, chunks, doc_vectors)
        indexed += len(chunks)
        if on_progress is not None:
            on_progress(done, len(pending))

    logger.info("ingest_complete", documents=len(pending), chunks=indexed)
    return indexed


async def retrieve(
    session: AsyncSession,
    query: str,
    language: Language | None,
) -> list[RetrievedChunk]:
    """Hybrid search → optional rerank → top-k chunks with source metadata."""

    settings = get_settings()
    candidates = await hybrid_search(session, query, language, settings.retrieval_candidates)
    if settings.rerank_enabled:
        from abb_rag.rerank import rerank

        return await rerank(query, candidates, settings.retrieval_top_k)
    return candidates[: settings.retrieval_top_k]
