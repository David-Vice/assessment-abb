from uuid import UUID

from abb_contracts import AnswerStatus, ChatTurn
from abb_rag import ExternalServiceError
from langchain_core.messages import HumanMessage, SystemMessage

from abb_chat.llm import get_aux_model, message_text
from abb_chat.persistence import fetch_recent_turns
from abb_chat.prompts import QUERY_REWRITE_SYSTEM

# Up to 6 recent answered turns — enough for follow-ups without unbounded context.
RECENT_TURNS_LIMIT = 6


async def load_history(session_id: UUID) -> list[ChatTurn]:
    """Recent answered turns only — refusals/errors are not trustworthy context."""

    turns = await fetch_recent_turns(session_id, RECENT_TURNS_LIMIT)
    return [turn for turn in turns if turn.status is AnswerStatus.ANSWERED and turn.answer.strip()]


async def rewrite_query(question: str, history: list[ChatTurn]) -> str:
    """Rewrite a follow-up into a standalone query using recent turns."""

    if not history:
        return question
    conversation = "\n".join(f"User: {turn.question}\nAssistant: {turn.answer}" for turn in history)
    messages = [
        SystemMessage(content=QUERY_REWRITE_SYSTEM),
        HumanMessage(content=f"Conversation:\n{conversation}\n\nFollow-up: {question}"),
    ]
    try:
        response = await get_aux_model().ainvoke(messages)
    except Exception as error:
        raise ExternalServiceError(f"query rewrite failed: {error}") from error
    return message_text(response.content).strip() or question
