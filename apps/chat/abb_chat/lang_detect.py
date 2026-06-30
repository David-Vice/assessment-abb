from functools import lru_cache
from typing import TYPE_CHECKING

from abb_contracts import Language

if TYPE_CHECKING:
    from py3langid.langid import LanguageIdentifier

# Minimum question length worth running the classifier on. Below this threshold
# ("ABB?", "OK") the trigram model lacks enough signal; fall back to the UI hint.
_MIN_CHARS = 20
# Maximum sample fed to the classifier — questions are short, but cap is cheap insurance.
_SAMPLE_CHARS = 500
# Same confidence bar as the scraper's reconcile_language: low-probability outputs
# (bilingual text, transliterations, typo-heavy messages) fall back to the hint.
_MIN_CONFIDENCE = 0.85


@lru_cache(maxsize=1)
def _identifier() -> "LanguageIdentifier":
    """Load and pin the py3langid model, restricted to the three supported languages."""
    from py3langid.langid import MODEL_FILE, LanguageIdentifier

    identifier = LanguageIdentifier.from_pickled_model(MODEL_FILE, norm_probs=True)
    identifier.set_languages([Language.AZ.value, Language.EN.value, Language.RU.value])
    return identifier


def auto_language(text: str, hint: Language) -> Language:
    """Detect the language of *text*; return *hint* when detection is uncertain.

    Called once per chat request so each question can trigger a language switch
    independently — asking in English after an Azerbaijani question just works.
    The *hint* (the UI-selected language) is the authoritative fallback for short
    or ambiguous inputs.
    """
    stripped = text.strip()
    if len(stripped) < _MIN_CHARS:
        return hint
    try:
        code, confidence = _identifier().classify(stripped[:_SAMPLE_CHARS])
        if confidence < _MIN_CONFIDENCE:
            return hint
        return Language(code)
    except Exception:
        return hint
