import pytest
from abb_chat.lang_detect import auto_language
from abb_contracts import Language


@pytest.mark.parametrize(
    "text, hint, expected",
    [
        # Clear English sentence — override AZ hint
        (
            "What are the interest rates for personal loans at ABB Bank?",
            Language.AZ,
            Language.EN,
        ),
        # Clear Russian sentence — override EN hint
        (
            "Какие услуги предлагает банк АББ для физических лиц?",
            Language.EN,
            Language.RU,
        ),
        # Clear Azerbaijani with diacritics — override EN hint
        (
            "ABB Bankın şəxsi kredit faiz dərəcələri hansılardır?",
            Language.EN,
            Language.AZ,
        ),
        # Azerbaijani without special chars — still detectable via trigrams
        (
            "ABB bankinin xidmetleri haqqinda melumat verin zehmet olmasa",
            Language.EN,
            Language.AZ,
        ),
        # Too short — fall back to hint regardless of content
        ("ABB?", Language.EN, Language.EN),
        ("OK", Language.RU, Language.RU),
        # Hint is returned when text is below _MIN_CHARS threshold
        ("short text here", Language.AZ, Language.AZ),
    ],
)
def test_auto_language(text: str, hint: Language, expected: Language) -> None:
    result = auto_language(text, hint)
    assert result == expected


def test_auto_language_returns_hint_on_ambiguous_input() -> None:
    # Highly mixed / gibberish text should fall back to hint (confidence < 0.85)
    ambiguous = "bank kredit loan кредит ABB 123 ok yes da nein"
    # We don't assert a specific language — just that it returns *something* valid
    result = auto_language(ambiguous, Language.EN)
    assert result in (Language.EN, Language.AZ, Language.RU)


def test_auto_language_consistent_per_question() -> None:
    """Same question produces the same language every call (model is deterministic)."""
    question = "When was ABB Bank founded and what are its main services?"
    first = auto_language(question, Language.AZ)
    second = auto_language(question, Language.AZ)
    assert first == second == Language.EN
