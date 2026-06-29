import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from abb_rag.models import Chunk

# A chunk whose normalized text recurs verbatim across at least this many
# distinct pages is cross-page boilerplate (e.g. the repeated promo/footer
# block), not real content — drop it before embedding.
BOILERPLATE_MIN_DOCS = 8
# Length guard: only *short* recurring chunks are treated as boilerplate. A long
# chunk repeated across pages is a substantive shared disclosure (fees, terms) —
# never drop it, even if it recurs. Protects recall against false positives.
BOILERPLATE_MAX_CHARS = 400

_WHITESPACE = re.compile(r"\s+")


def normalize(content: str) -> str:
    return _WHITESPACE.sub(" ", content.strip().lower())


def find_boilerplate(
    per_document_chunks: Sequence[Sequence[Chunk]],
    min_docs: int = BOILERPLATE_MIN_DOCS,
) -> set[str]:
    """Keys of *short* chunks that recur across `min_docs`+ distinct documents."""

    document_frequency: Counter[str] = Counter()
    for chunks in per_document_chunks:
        for key in {normalize(chunk.content) for chunk in chunks}:
            document_frequency[key] += 1
    return {
        key
        for key, count in document_frequency.items()
        if count >= min_docs and len(key) <= BOILERPLATE_MAX_CHARS
    }


def dedup_chunks(chunks: Sequence[Chunk], boilerplate: set[str]) -> list[Chunk]:
    """Drop boilerplate + intra-document duplicates, then re-number ordinals."""

    seen: set[str] = set()
    kept: list[Chunk] = []
    for chunk in chunks:
        key = normalize(chunk.content)
        if key in boilerplate or key in seen:
            continue
        seen.add(key)
        kept.append(chunk)
    return [replace(chunk, ordinal=ordinal) for ordinal, chunk in enumerate(kept)]
