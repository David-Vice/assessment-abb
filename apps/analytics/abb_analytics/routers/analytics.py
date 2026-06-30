from datetime import UTC, datetime, timedelta
from typing import Annotated

from abb_contracts import (
    AnalyticsSummary,
    DistributionStats,
    Language,
    PerformanceStats,
    QualityStats,
    TopQuestion,
    VolumeSeries,
)
from fastapi import APIRouter, Query, Request

from abb_analytics import queries
from abb_analytics.cache import cached

router = APIRouter(prefix="/analytics", tags=["analytics"])

DEFAULT_RANGE_DAYS = 30
TOP_QUESTIONS_LIMIT = 10

# Shared query-param types so every endpoint exposes the same filter contract.
FromParam = Annotated[datetime | None, Query(alias="from")]
ToParam = Annotated[datetime | None, Query(alias="to")]
LangParam = Annotated[Language | None, Query()]


def _resolve_range(from_ts: datetime | None, to_ts: datetime | None) -> tuple[datetime, datetime]:
    end = to_ts or datetime.now(UTC)
    start = from_ts or (end - timedelta(days=DEFAULT_RANGE_DAYS))
    return start, end


def _redis(request: Request) -> object:
    return getattr(request.app.state, "redis", None)


def _key(
    name: str,
    start: datetime,
    end: datetime,
    language: Language | None,
    extra: str = "",
) -> str:
    lang = language.value if language is not None else "all"
    return f"{name}:{start.isoformat()}:{end.isoformat()}:{lang}:{extra}"


@router.get("/summary", response_model=AnalyticsSummary)
async def summary(
    request: Request, from_ts: FromParam = None, to_ts: ToParam = None, lang: LangParam = None
) -> AnalyticsSummary:
    start, end = _resolve_range(from_ts, to_ts)
    return await cached(
        _redis(request),  # type: ignore[arg-type]
        _key("summary", start, end, lang),
        AnalyticsSummary,
        lambda: queries.get_summary(start, end, lang),
    )


@router.get("/volume", response_model=VolumeSeries)
async def volume(
    request: Request,
    from_ts: FromParam = None,
    to_ts: ToParam = None,
    lang: LangParam = None,
    bucket: Annotated[str, Query()] = "day",
) -> VolumeSeries:
    start, end = _resolve_range(from_ts, to_ts)
    return await cached(
        _redis(request),  # type: ignore[arg-type]
        _key("volume", start, end, lang, bucket),
        VolumeSeries,
        lambda: queries.get_volume(start, end, bucket, lang),
    )


@router.get("/top-questions", response_model=list[TopQuestion])
async def top_questions(
    request: Request, from_ts: FromParam = None, to_ts: ToParam = None, lang: LangParam = None
) -> list[TopQuestion]:
    start, end = _resolve_range(from_ts, to_ts)
    return await queries.get_top_questions(start, end, TOP_QUESTIONS_LIMIT, lang)


@router.get("/performance", response_model=PerformanceStats)
async def performance(
    request: Request, from_ts: FromParam = None, to_ts: ToParam = None, lang: LangParam = None
) -> PerformanceStats:
    start, end = _resolve_range(from_ts, to_ts)
    return await cached(
        _redis(request),  # type: ignore[arg-type]
        _key("performance", start, end, lang),
        PerformanceStats,
        lambda: queries.get_performance(start, end, lang),
    )


@router.get("/quality", response_model=QualityStats)
async def quality(
    request: Request, from_ts: FromParam = None, to_ts: ToParam = None, lang: LangParam = None
) -> QualityStats:
    start, end = _resolve_range(from_ts, to_ts)
    return await cached(
        _redis(request),  # type: ignore[arg-type]
        _key("quality", start, end, lang),
        QualityStats,
        lambda: queries.get_quality(start, end, lang),
    )


@router.get("/distribution", response_model=DistributionStats)
async def distribution(
    request: Request, from_ts: FromParam = None, to_ts: ToParam = None, lang: LangParam = None
) -> DistributionStats:
    start, end = _resolve_range(from_ts, to_ts)
    return await cached(
        _redis(request),  # type: ignore[arg-type]
        _key("distribution", start, end, lang),
        DistributionStats,
        lambda: queries.get_distribution(start, end, lang),
    )
