from datetime import UTC, datetime

from abb_contracts import CorpusDocument, Language, Segment
from abb_rag.chunking import MAX_CHUNK_TOKENS, chunk_document


def _doc(markdown: str) -> CorpusDocument:
    return CorpusDocument(
        url="https://abb-bank.az/en/ferdi/kartlar",
        language=Language.EN,
        segment=Segment.INDIVIDUALS,
        title="Cards",
        markdown=markdown,
        content_hash="sha256:x",
        fetched_at=datetime.now(UTC),
    )


def test_short_document_is_a_single_chunk() -> None:
    # Arrange
    doc = _doc("ABB offers debit and credit cards for everyday payments.")

    # Act
    chunks = chunk_document(doc)

    # Assert
    assert len(chunks) == 1
    assert chunks[0].ordinal == 0
    assert chunks[0].token_count > 0
    assert "cards" in chunks[0].content.lower()


def test_long_document_splits_into_multiple_bounded_chunks() -> None:
    # Arrange — ~2000 tokens, no headings.
    doc = _doc(" ".join(["payment"] * 2000))

    # Act
    chunks = chunk_document(doc)

    # Assert
    assert len(chunks) > 1
    assert all(c.token_count <= MAX_CHUNK_TOKENS for c in chunks)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_trivially_short_chunks_are_dropped() -> None:
    # Arrange — a real section plus a stray heading-only section ("## B").
    doc = _doc("# A\n\nThis is a real paragraph with plenty of tokens to keep it.\n\n## B")

    # Act
    chunks = chunk_document(doc)

    # Assert — the tiny "## B" chunk is dropped; only the real section survives.
    assert len(chunks) == 1
    assert "## B" not in chunks[0].content


def test_headings_become_breadcrumbs_on_chunks() -> None:
    # Arrange
    doc = _doc("# Bank Cards\n\nIntro text.\n\n## Fees\n\nFee details here.")

    # Act
    chunks = chunk_document(doc)

    # Assert — each section's heading is preserved in its chunk text.
    joined = "\n".join(c.content for c in chunks)
    assert "# Bank Cards" in joined
    assert "## Fees" in joined
