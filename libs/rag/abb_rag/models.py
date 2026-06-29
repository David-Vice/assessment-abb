from dataclasses import dataclass

from abb_contracts import Language, Segment


@dataclass(frozen=True, slots=True)
class Chunk:
    """A token-budgeted slice of a document, ready to embed."""

    url: str
    ordinal: int
    content: str
    language: Language
    segment: Segment
    token_count: int
    title: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk returned from retrieval, with its fused/rerank score."""

    chunk_id: int
    content: str
    url: str
    language: Language
    segment: Segment
    title: str | None
    score: float
