from datetime import datetime
from typing import Any

from abb_contracts import (
    AnalyticsSummary,
    DistributionStats,
    Language,
    PerformanceStats,
    QualityStats,
    Segment,
    TimeBucket,
    TopQuestion,
    VolumeSeries,
)
from abb_rag import ExternalServiceError, session_scope
from sqlalchemy import Result, TextClause, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

# Approximate gpt-4o pricing (USD per 1M tokens). Cost is a demo-grade estimate,
# not billing truth; the per-row model field could refine this later.
_USD_PER_1M_PROMPT = 2.50
_USD_PER_1M_COMPLETION = 10.00

# Bound, validated whitelist for date_trunc's first argument: Postgres only
# accepts known units, and we never pass anything else through.
_ALLOWED_BUCKETS = ("hour", "day")

# Every query shares the same time-and-language predicate. `:lang` may be NULL to
# mean "all languages" (same NULL-guard idiom as the retriever). SQL is built from
# string *literals* (no interpolation) so the only variables are bound parameters.
_SUMMARY_SQL = text(
    "SELECT COUNT(*) AS total, "
    "COUNT(*) FILTER (WHERE status = 'answered') AS answered, "
    "COALESCE(AVG(latency_ms), 0) AS avg_latency "
    "FROM chat_logs "
    "WHERE created_at >= :from_ts AND created_at < :to_ts "
    "AND (CAST(:lang AS text) IS NULL OR language = :lang)"
)

_VOLUME_SQL = text(
    "SELECT date_trunc(:bucket, created_at) AS bucket, COUNT(*) AS n "
    "FROM chat_logs "
    "WHERE created_at >= :from_ts AND created_at < :to_ts "
    "AND (CAST(:lang AS text) IS NULL OR language = :lang) "
    "GROUP BY bucket ORDER BY bucket"
)

_TOP_QUESTIONS_SQL = text(
    "SELECT question, COUNT(*) AS n "
    "FROM chat_logs "
    "WHERE created_at >= :from_ts AND created_at < :to_ts "
    "AND (CAST(:lang AS text) IS NULL OR language = :lang) "
    "GROUP BY question ORDER BY n DESC, question ASC LIMIT :limit"
)

_PERFORMANCE_SQL = text(
    "SELECT COALESCE(AVG(latency_ms), 0) AS avg_latency, "
    "COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms), 0) AS p95_latency, "
    "COALESCE(AVG(prompt_tokens + completion_tokens), 0) AS avg_tokens, "
    "COALESCE(SUM(prompt_tokens), 0) AS sum_prompt, "
    "COALESCE(SUM(completion_tokens), 0) AS sum_completion "
    "FROM chat_logs "
    "WHERE created_at >= :from_ts AND created_at < :to_ts "
    "AND (CAST(:lang AS text) IS NULL OR language = :lang)"
)

_QUALITY_SQL = text(
    "SELECT status, COUNT(*) AS n "
    "FROM chat_logs "
    "WHERE created_at >= :from_ts AND created_at < :to_ts "
    "AND (CAST(:lang AS text) IS NULL OR language = :lang) "
    "GROUP BY status"
)

_DISTRIBUTION_LANG_SQL = text(
    "SELECT language, COUNT(*) AS n "
    "FROM chat_logs "
    "WHERE created_at >= :from_ts AND created_at < :to_ts "
    "AND (CAST(:lang AS text) IS NULL OR language = :lang) "
    "AND language IS NOT NULL "
    "GROUP BY language"
)

# Segment lives on each citation (JSONB), not on the row; unnest to count the
# segment mix of the sources actually used to answer.
_DISTRIBUTION_SEG_SQL = text(
    "SELECT elem->>'segment' AS segment, COUNT(*) AS n "
    "FROM chat_logs, jsonb_array_elements(citations) AS elem "
    "WHERE created_at >= :from_ts AND created_at < :to_ts "
    "AND (CAST(:lang AS text) IS NULL OR language = :lang) "
    "GROUP BY elem->>'segment'"
)


def _params(
    from_ts: datetime, to_ts: datetime, language: Language | None
) -> dict[str, object]:
    return {
        "from_ts": from_ts,
        "to_ts": to_ts,
        "lang": language.value if language is not None else None,
    }


async def get_summary(
    from_ts: datetime, to_ts: datetime, language: Language | None
) -> AnalyticsSummary:
    async with session_scope() as session:
        row = (await _execute(session, _SUMMARY_SQL, _params(from_ts, to_ts, language))).one()
    total = int(row.total)
    return AnalyticsSummary(
        total_questions=total,
        answered_rate=(int(row.answered) / total) if total else 0.0,
        avg_latency_ms=float(row.avg_latency),
    )


async def get_volume(
    from_ts: datetime, to_ts: datetime, bucket: str, language: Language | None
) -> VolumeSeries:
    if bucket not in _ALLOWED_BUCKETS:
        bucket = "day"
    params = {**_params(from_ts, to_ts, language), "bucket": bucket}
    async with session_scope() as session:
        rows = (await _execute(session, _VOLUME_SQL, params)).all()
    return VolumeSeries(
        points=[TimeBucket(bucket=row.bucket, count=int(row.n)) for row in rows]
    )


async def get_top_questions(
    from_ts: datetime, to_ts: datetime, limit: int, language: Language | None
) -> list[TopQuestion]:
    params = {**_params(from_ts, to_ts, language), "limit": limit}
    async with session_scope() as session:
        rows = (await _execute(session, _TOP_QUESTIONS_SQL, params)).all()
    return [TopQuestion(question=row.question, count=int(row.n)) for row in rows]


async def get_performance(
    from_ts: datetime, to_ts: datetime, language: Language | None
) -> PerformanceStats:
    async with session_scope() as session:
        row = (await _execute(session, _PERFORMANCE_SQL, _params(from_ts, to_ts, language))).one()
    cost = (
        int(row.sum_prompt) / 1_000_000 * _USD_PER_1M_PROMPT
        + int(row.sum_completion) / 1_000_000 * _USD_PER_1M_COMPLETION
    )
    return PerformanceStats(
        avg_latency_ms=float(row.avg_latency),
        p95_latency_ms=float(row.p95_latency),
        avg_total_tokens=float(row.avg_tokens),
        estimated_cost_usd=round(cost, 4),
    )


async def get_quality(
    from_ts: datetime, to_ts: datetime, language: Language | None
) -> QualityStats:
    async with session_scope() as session:
        rows = (await _execute(session, _QUALITY_SQL, _params(from_ts, to_ts, language))).all()
    counts = {row.status: int(row.n) for row in rows}
    return QualityStats(
        answered=counts.get("answered", 0),
        declined_off_topic=counts.get("declined_off_topic", 0),
        declined_injection=counts.get("declined_injection", 0),
        error=counts.get("error", 0),
    )


async def get_distribution(
    from_ts: datetime, to_ts: datetime, language: Language | None
) -> DistributionStats:
    params = _params(from_ts, to_ts, language)
    async with session_scope() as session:
        lang_rows = (await _execute(session, _DISTRIBUTION_LANG_SQL, params)).all()
        seg_rows = (await _execute(session, _DISTRIBUTION_SEG_SQL, params)).all()
    return DistributionStats(
        by_language={Language(row.language): int(row.n) for row in lang_rows},
        by_segment={
            Segment(row.segment): int(row.n)
            for row in seg_rows
            if row.segment is not None
        },
    )


async def _execute(
    session: AsyncSession, sql: TextClause, params: dict[str, object]
) -> Result[Any]:
    try:
        return await session.execute(sql, params)
    except SQLAlchemyError as error:
        raise ExternalServiceError(f"analytics query failed: {error}") from error
