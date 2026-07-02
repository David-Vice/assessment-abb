import pytest
from abb_chat.prompts import is_social_opener, social_welcome
from abb_contracts import Language


@pytest.mark.parametrize(
    "text",
    ["Hi", "hello!", "  Salam  ", "thank you", "привет.", "HEY THERE"],
)
def test_is_social_opener_accepts_greetings(text: str) -> None:
    assert is_social_opener(text)


@pytest.mark.parametrize(
    "text",
    ["What is the minimum cash loan amount?", "weather today", "hi can you help with loans"],
)
def test_is_social_opener_rejects_questions(text: str) -> None:
    assert not is_social_opener(text)


def test_social_welcome_returns_localized_message() -> None:
    assert "ABB Bank" in social_welcome(Language.EN)
    assert "ABB Bank" in social_welcome(Language.AZ)
    assert "ABB Bank" in social_welcome(Language.RU)
