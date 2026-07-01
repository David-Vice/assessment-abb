import pytest
from abb_chat.llm import MAX_RETRIES, get_aux_model, get_chat_model, message_text
from abb_rag.settings import get_settings


def test_models_configured_with_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    get_chat_model.cache_clear()
    get_aux_model.cache_clear()

    assert get_chat_model().max_retries == MAX_RETRIES
    assert get_aux_model().max_retries == MAX_RETRIES


def test_message_text_flattens_string_and_blocks() -> None:
    # Arrange & Act & Assert
    assert message_text("hi") == "hi"
    assert message_text(["x", "y"]) == "xy"
    assert message_text([{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]) == "ab"
