from abb_chat.context import build_context, to_citations
from abb_contracts import Language, Segment
from abb_rag import RetrievedChunk


def _chunk(chunk_id: int, url: str, content: str = "body text") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        content=content,
        url=url,
        language=Language.EN,
        segment=Segment.INDIVIDUALS,
        title="T",
        score=1.0,
    )


def test_to_citations_dedups_by_url_keeping_order() -> None:
    # Arrange — two chunks from the same page, one from another.
    chunks = [
        _chunk(1, "https://abb-bank.az/en/cards"),
        _chunk(2, "https://abb-bank.az/en/cards"),
        _chunk(3, "https://abb-bank.az/en/loans"),
    ]

    # Act
    citations = to_citations(chunks)

    # Assert
    assert [c.url for c in citations] == [
        "https://abb-bank.az/en/cards",
        "https://abb-bank.az/en/loans",
    ]


def test_build_context_stops_at_token_budget() -> None:
    # Arrange — each block is large; a tiny budget admits only the first.
    chunks = [_chunk(i, f"https://abb-bank.az/{i}", content="word " * 200) for i in range(5)]

    # Act
    context = build_context(chunks, token_budget=50)

    # Assert
    assert context.count("[Source") == 1


def test_build_context_includes_all_within_large_budget() -> None:
    # Arrange
    chunks = [_chunk(i, f"https://abb-bank.az/{i}") for i in range(3)]

    # Act
    context = build_context(chunks, token_budget=10_000)

    # Assert
    assert context.count("[Source") == 3
