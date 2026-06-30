from collections.abc import AsyncIterator
from dataclasses import dataclass

from abb_contracts import ChatTurn, Language
from abb_rag import ExternalServiceError, get_settings

from abb_chat.llm import get_chat_model, message_text
from abb_chat.prompts import build_chat_messages


@dataclass(slots=True)
class TokenUsage:
    """Accumulated token counts for one generation (filled as the stream ends)."""

    prompt_tokens: int = 0
    completion_tokens: int = 0


async def stream_answer(
    question: str,
    language: Language,
    context: str,
    history: list[ChatTurn],
    usage: TokenUsage,
) -> AsyncIterator[str]:
    """Stream the grounded answer token-by-token; record token usage into `usage`.

    `usage` is mutated in place because token counts only arrive on the final
    streamed chunk (`stream_usage=True`), after all text has been yielded.
    """

    messages = build_chat_messages(
        question, language, context, history, get_settings().context_token_budget
    )
    try:
        async for chunk in get_chat_model().astream(messages):
            metadata = getattr(chunk, "usage_metadata", None)
            if metadata:
                usage.prompt_tokens = metadata.get("input_tokens", usage.prompt_tokens)
                usage.completion_tokens = metadata.get("output_tokens", usage.completion_tokens)
            text = message_text(chunk.content)
            if text:
                yield text
    except Exception as error:
        raise ExternalServiceError(f"generation failed: {error}") from error
