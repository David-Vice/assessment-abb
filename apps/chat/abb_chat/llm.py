from functools import lru_cache

from abb_rag import get_settings
from langchain_openai import ChatOpenAI

CHAT_TEMPERATURE = 0.2
AUX_TEMPERATURE = 0.0
REQUEST_TIMEOUT_SECONDS = 60.0
# Retry/backoff on rate-limit/timeout for every OpenAI call (no silent hang).
MAX_RETRIES = 5


@lru_cache
def get_chat_model() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.chat_model,
        openai_api_key=settings.openai_api_key.get_secret_value(),
        temperature=CHAT_TEMPERATURE,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=MAX_RETRIES,
    )


@lru_cache
def get_aux_model() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings.aux_model,
        openai_api_key=settings.openai_api_key.get_secret_value(),
        temperature=AUX_TEMPERATURE,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=MAX_RETRIES,
    )


def message_text(content: str | list[str | dict[str, object]]) -> str:
    """Flatten LangChain message content (str or content blocks) to plain text."""

    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)
