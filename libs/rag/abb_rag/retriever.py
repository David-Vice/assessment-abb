from typing import Any

from abb_contracts import Language, Segment
from sqlalchemy import Row, TextClause, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from abb_rag.embeddings import embed_query
from abb_rag.exceptions import ExternalServiceError
from abb_rag.log import get_logger
from abb_rag.models import RetrievedChunk
from abb_rag.rrf import reciprocal_rank_fusion
from abb_rag.vectorstore import to_halfvec

logger = get_logger(__name__)

_DENSE_SQL = text(
    "SELECT c.id, c.content, c.language, c.segment, d.url, d.title "
    "FROM chunks c JOIN documents d ON d.id = c.document_id "
    "WHERE (CAST(:lang AS text) IS NULL OR c.language = :lang) AND c.embedding IS NOT NULL "
    "ORDER BY c.embedding <=> (:qemb)::halfvec "
    "LIMIT :limit"
)

# Sparse = uniform 'simple'+unaccent full-text (equal for az/ru/en) widened by
# pg_trgm word-similarity for typos/inflections. The `<%` operator (over the
# immutable_unaccent(content) trigram index) is index-usable; word_similarity in
# ORDER BY only scores the already-matched rows. No language stemmer is used.
_SPARSE_SQL = text(
    "SELECT c.id, c.content, c.language, c.segment, d.url, d.title "
    "FROM chunks c JOIN documents d ON d.id = c.document_id "
    "WHERE (CAST(:lang AS text) IS NULL OR c.language = :lang) AND ("
    "  c.tsv @@ websearch_to_tsquery('simple', immutable_unaccent(:q)) "
    "  OR immutable_unaccent(:q) <% immutable_unaccent(c.content)) "
    "ORDER BY ts_rank(c.tsv, websearch_to_tsquery('simple', immutable_unaccent(:q))) DESC, "
    "  word_similarity(immutable_unaccent(:q), immutable_unaccent(c.content)) DESC "
    "LIMIT :limit"
)


async def hybrid_search(
    session: AsyncSession,
    query: str,
    language: Language | None,
    candidates: int,
) -> list[RetrievedChunk]:
    """Dense ANN + sparse full-text/trigram, fused with RRF, language-aware."""

    query_embedding = await embed_query(query)
    dense = await _search(
        session, _DENSE_SQL, {"qemb": to_halfvec(query_embedding)}, language, candidates
    )
    sparse = await _search(session, _SPARSE_SQL, {"q": query}, language, candidates)

    rows_by_id: dict[int, Row[Any]] = {int(row.id): row for row in (*dense, *sparse)}
    scores = reciprocal_rank_fusion([[int(r.id) for r in dense], [int(r.id) for r in sparse]])
    ranked = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)[:candidates]
    logger.info(
        "hybrid_search",
        language=language.value if language is not None else None,
        dense=len(dense),
        sparse=len(sparse),
        fused=len(ranked),
    )
    return [_to_retrieved(rows_by_id[chunk_id], scores[chunk_id]) for chunk_id in ranked]


async def _search(
    session: AsyncSession,
    sql: TextClause,
    params: dict[str, object],
    language: Language | None,
    limit: int,
) -> list[Row[Any]]:
    lang = language.value if language is not None else None
    try:
        rows = list((await session.execute(sql, {**params, "lang": lang, "limit": limit})).all())
        # Cross-language fallback: fill only the deficit with other-language hits.
        if language is not None and len(rows) < limit:
            seen = {int(row.id) for row in rows}
            fallback = (await session.execute(sql, {**params, "lang": None, "limit": limit})).all()
            for row in fallback:
                if int(row.id) not in seen:
                    rows.append(row)
                    if len(rows) >= limit:
                        break
    except SQLAlchemyError as error:
        raise ExternalServiceError(f"retrieval query failed: {error}") from error
    return rows


def _to_retrieved(row: Row[Any], score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=int(row.id),
        content=row.content,
        url=row.url,
        language=Language(row.language),
        segment=Segment(row.segment) if row.segment else Segment.OTHER,
        title=row.title,
        score=score,
    )
