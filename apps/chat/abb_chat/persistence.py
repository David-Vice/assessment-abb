import json
from typing import Any
from uuid import UUID

from abb_contracts import AnswerStatus, ChatTurn, Citation, Language
from abb_rag import session_scope
from sqlalchemy import Row, text

_INSERT = text(
    "INSERT INTO chat_logs "
    "(session_id, question, answer, language, status, citations, retrieved_ids, model, latency_ms) "
    "VALUES "
    "(CAST(:session_id AS uuid), :question, :answer, :language, :status, "
    "CAST(:citations AS jsonb), :retrieved_ids, :model, :latency_ms) "
    "RETURNING id"
)

_SELECT_RECENT = text(
    "SELECT id, session_id, question, answer, language, status, citations, created_at "
    "FROM chat_logs WHERE session_id = CAST(:session_id AS uuid) "
    "ORDER BY created_at DESC LIMIT :limit"
)


async def insert_chat_log(
    *,
    session_id: UUID,
    question: str,
    answer: str,
    language: Language,
    status: AnswerStatus,
    citations: list[Citation],
    retrieved_ids: list[int],
    model: str,
    latency_ms: int,
) -> int:
    """Persist a Q/A turn (with citations + timestamp) and return its id."""

    citations_json = json.dumps([citation.model_dump(mode="json") for citation in citations])
    async with session_scope() as session:
        result = await session.execute(
            _INSERT,
            {
                "session_id": str(session_id),
                "question": question,
                "answer": answer,
                "language": language.value,
                "status": status.value,
                "citations": citations_json,
                "retrieved_ids": retrieved_ids,
                "model": model,
                "latency_ms": latency_ms,
            },
        )
        return int(result.scalar_one())


async def fetch_recent_turns(session_id: UUID, limit: int) -> list[ChatTurn]:
    """Most recent turns for a session, returned in chronological order."""

    async with session_scope() as session:
        rows = (
            await session.execute(_SELECT_RECENT, {"session_id": str(session_id), "limit": limit})
        ).all()
    turns = [_to_turn(row) for row in rows]
    turns.reverse()
    return turns


def _to_turn(row: Row[Any]) -> ChatTurn:
    return ChatTurn(
        id=int(row.id),
        session_id=row.session_id,
        question=row.question,
        answer=row.answer,
        language=Language(row.language) if row.language else None,
        status=AnswerStatus(row.status),
        citations=[Citation.model_validate(item) for item in row.citations],
        created_at=row.created_at,
    )
