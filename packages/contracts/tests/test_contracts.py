from datetime import UTC, datetime
from uuid import uuid4

import pytest
from abb_contracts import ChatRequest, Corpus, CorpusDocument, Language, Segment
from pydantic import ValidationError


def test_corpus_document_rejects_unknown_fields() -> None:
    # Arrange
    payload = {
        "url": "https://abb-bank.az/en/ferdi",
        "language": "en",
        "markdown": "# Hi",
        "content_hash": "sha256:abc",
        "fetched_at": datetime.now(UTC),
        "unexpected": "x",
    }

    # Act & Assert
    with pytest.raises(ValidationError):
        CorpusDocument.model_validate(payload)


def test_corpus_document_defaults_segment_to_other() -> None:
    # Arrange
    doc = CorpusDocument(
        url="https://abb-bank.az/en/ferdi",
        language=Language.EN,
        markdown="# Hi",
        content_hash="sha256:abc",
        fetched_at=datetime.now(UTC),
    )

    # Act & Assert
    assert doc.segment is Segment.OTHER


def test_corpus_roundtrips_through_json() -> None:
    # Arrange
    corpus = Corpus(
        source="abb-bank.az",
        generated_at=datetime.now(UTC),
        documents=[
            CorpusDocument(
                url="https://abb-bank.az/ru/biznes",
                language=Language.RU,
                segment=Segment.BUSINESS,
                markdown="# Бизнес",
                content_hash="sha256:def",
                fetched_at=datetime.now(UTC),
            )
        ],
    )

    # Act
    restored = Corpus.model_validate_json(corpus.model_dump_json())

    # Assert
    assert restored.documents[0].language is Language.RU


def test_chat_request_enforces_question_length() -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        ChatRequest(session_id=uuid4(), question="", language=Language.EN)
