from collections.abc import AsyncIterator

from abb_contracts import ChatTurn, Language
from abb_rag import ExternalServiceError

from abb_chat.llm import get_chat_model, message_text
from abb_chat.prompts import build_chat_messages


async def stream_answer(
    question: str,
    language: Language,
    context: str,
    history: list[ChatTurn],
) -> AsyncIterator[str]:
    """Stream the grounded answer token-by-token from the chat model."""

    messages = build_chat_messages(question, language, context, history)
    try:
        async for chunk in get_chat_model().astream(messages):
            text = message_text(chunk.content)
            if text:
                yield text
    except Exception as error:
        raise ExternalServiceError(f"generation failed: {error}") from error
