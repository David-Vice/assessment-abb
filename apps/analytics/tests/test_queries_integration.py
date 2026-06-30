"""DB-backed integration tests for the analytics SQL layer.

`test_queries.py` mocks the session, so it only proves the Python-side mapping
and math; the actual `date_trunc`, `percentile_cont`, `GROUP BY`, and
`jsonb_array_elements` SQL never executes there. These tests run the real
queries against the same Postgres the rest of the stack uses (see
`docker-compose.yml`), seeding a handful of `chat_logs` rows tagged under a
fixed sentinel `session_id` and always deleting them afterward (`finally`),
so the live demo database is never left with leftover test data.

Isolation caveat: assertions use a tight (few-second) time window around the
insert rather than a transaction rollback, because the query functions each
open their own session via `session_scope()`. This is correct for a
single-developer / CI run with no concurrent chat traffic, which is the scope
of this demo project — not a claim of safe concurrent-test isolation.

Skipped automatically if Postgres is unreachable — e.g. `docker compose` is
down, or (on some Windows dev machines) a native Postgres install is also
bound to port 5432 and answers instead of the docker-published one; see the
`POSTGRES_HOST_PORT` override in `docker-compose.yml`.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from abb_analytics import queries
from abb_contracts import Language
from abb_rag import session_scope
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

pytestmark = pytest.mark.asyncio

_SENTINEL_SESSION = uuid.uuid4()

_INSERT_SQL = text(
    "INSERT INTO chat_logs "
    "(session_id, question, answer, language, status, citations, "
    "model, prompt_tokens, completion_tokens, latency_ms) "
    "VALUES (:session_id, :question, :answer, :language, :status, "
    "CAST(:citations AS jsonb), :model, :prompt_tokens, :completion_tokens, :latency_ms)"
)
_DELETE_SQL = text("DELETE FROM chat_logs WHERE session_id = :session_id")


def _row(
    language: str,
    status: str,
    latency_ms: int,
    prompt_tokens: int,
    completion_tokens: int,
    segment: str | None,
    question: str,
) -> dict[str, object]:
    citations = [] if segment is None else [{"url": "https://abb-bank.az/x", "segment": segment}]
    return {
        "session_id": str(_SENTINEL_SESSION),
        "question": question,
        "answer": "integration test answer",
        "language": language,
        "status": status,
        "citations": json.dumps(citations),
        "model": "test-model",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms": latency_ms,
    }


# 3 answered (2 en, 1 az; citations: individuals, business, about) + 1 declined
# + 1 error. Declined/error rows must NOT affect performance KPIs (#4 scoping).
_SEEDED_ROWS = [
    _row("en", "answered", 100, 50, 20, "individuals", "How do I open an account?"),
    _row("en", "answered", 300, 80, 40, "business", "How do I open an account?"),
    _row("az", "answered", 200, 60, 30, "about", "Kart necə sifariş edilir?"),
    _row("en", "declined_off_topic", 5, 0, 0, None, "What is the weather today?"),
    _row("en", "error", 1, 0, 0, None, "Trigger an error"),
]


@pytest.fixture
async def seeded() -> AsyncGenerator[tuple[datetime, datetime], None]:
    window_start = datetime.now(UTC) - timedelta(seconds=1)
    try:
        async with session_scope() as session:
            for row in _SEEDED_ROWS:
                await session.execute(_INSERT_SQL, row)
    except (OperationalError, SQLAlchemyError) as error:
        pytest.skip(f"Postgres not reachable; skipping DB-backed integration tests ({error})")

    try:
        window_end = datetime.now(UTC) + timedelta(seconds=1)
        yield window_start, window_end
    finally:
        async with session_scope() as session:
            await session.execute(_DELETE_SQL, {"session_id": str(_SENTINEL_SESSION)})


async def test_summary_counts_real_rows(seeded: tuple[datetime, datetime]) -> None:
    start, end = seeded
    result = await queries.get_summary(start, end, None)

    assert result.total_questions == 5
    assert result.answered_rate == pytest.approx(3 / 5)


async def test_performance_scopes_to_answered(seeded: tuple[datetime, datetime]) -> None:
    start, end = seeded
    result = await queries.get_performance(start, end, None)

    # avg over the 3 answered rows only (100, 300, 200) — declined/error excluded.
    assert result.avg_latency_ms == pytest.approx(200.0)
    assert result.p95_latency_ms > 0
    # tokens: (50+80+60) prompt, (20+40+30) completion across answered rows only.
    assert result.estimated_cost_usd > 0


async def test_quality_groups_by_status_via_real_sql(seeded: tuple[datetime, datetime]) -> None:
    start, end = seeded
    result = await queries.get_quality(start, end, None)

    assert result.answered == 3
    assert result.declined_off_topic == 1
    assert result.declined_injection == 0
    assert result.error == 1


async def test_distribution_unnests_citations(seeded: tuple[datetime, datetime]) -> None:
    start, end = seeded
    result = await queries.get_distribution(start, end, None)

    assert result.by_language.get(Language.EN) == 4
    assert result.by_language.get(Language.AZ) == 1
    assert sum(result.by_segment.values()) == 3  # one citation per answered row


async def test_volume_date_trunc_groups_into_one_bucket(seeded: tuple[datetime, datetime]) -> None:
    start, end = seeded
    result = await queries.get_volume(start, end, "hour", None)

    assert sum(point.count for point in result.points) == 5


async def test_top_questions_groups_by_question(seeded: tuple[datetime, datetime]) -> None:
    start, end = seeded
    result = await queries.get_top_questions(start, end, 10, None)

    by_question = {q.question: q.count for q in result}
    assert by_question["How do I open an account?"] == 2


async def test_language_filter_narrows_real_query(seeded: tuple[datetime, datetime]) -> None:
    start, end = seeded
    result = await queries.get_summary(start, end, Language.AZ)

    assert result.total_questions == 1
