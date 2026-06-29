from abb_contracts import Language, Segment
from abb_rag.dedup import dedup_chunks, find_boilerplate
from abb_rag.models import Chunk


def _chunk(content: str, ordinal: int = 0) -> Chunk:
    return Chunk(
        url="https://abb-bank.az/en/x",
        ordinal=ordinal,
        content=content,
        language=Language.EN,
        segment=Segment.OTHER,
        token_count=len(content.split()),
    )


def test_find_boilerplate_flags_text_recurring_across_many_docs() -> None:
    # Arrange — a promo block on 8 pages, plus a unique body per page.
    promo = "Open a business account today"
    per_document = [[_chunk(promo), _chunk(f"unique body {i}")] for i in range(8)]

    # Act
    boilerplate = find_boilerplate(per_document)

    # Assert
    assert "open a business account today" in boilerplate
    assert "unique body 0" not in boilerplate


def test_find_boilerplate_respects_min_docs_threshold() -> None:
    # Arrange — repeated on only 3 docs, below the default threshold of 8.
    per_document = [[_chunk("repeated block")] for _ in range(3)]

    # Act & Assert
    assert find_boilerplate(per_document) == set()


def test_find_boilerplate_keeps_long_recurring_substantive_content() -> None:
    # Arrange — a long shared disclosure on 10 pages must NOT be flagged (length guard).
    long_text = "This is a substantive shared disclosure about fees and terms. " * 12
    per_document = [[_chunk(long_text)] for _ in range(10)]

    # Act & Assert
    assert find_boilerplate(per_document) == set()


def test_dedup_chunks_drops_boilerplate_and_intra_dups_and_renumbers() -> None:
    # Arrange
    chunks = [_chunk("Keep me", 0), _chunk("Promo", 1), _chunk("Keep me", 2), _chunk("Other", 3)]

    # Act
    result = dedup_chunks(chunks, boilerplate={"promo"})

    # Assert
    assert [c.content for c in result] == ["Keep me", "Other"]
    assert [c.ordinal for c in result] == [0, 1]
