from datetime import UTC, datetime

from abb_contracts import CorpusDocument, Language, Segment
from abb_scraper.sample import select_sample


def _doc(url: str, language: Language) -> CorpusDocument:
    return CorpusDocument(
        url=url,
        language=language,
        segment=Segment.OTHER,
        markdown="content body that is long enough",
        content_hash=f"sha256:{url}",
        fetched_at=datetime.now(UTC),
    )


def test_select_sample_respects_limit() -> None:
    # Arrange
    documents = [_doc(f"https://abb-bank.az/p{i}", Language.AZ) for i in range(10)]

    # Act
    sample = select_sample(documents, 4)

    # Assert
    assert len(sample) == 4


def test_select_sample_round_robins_languages_for_diversity() -> None:
    # Arrange — many AZ, few EN/RU; a head-slice would miss EN/RU.
    documents = [_doc(f"https://abb-bank.az/az{i}", Language.AZ) for i in range(8)]
    documents.append(_doc("https://abb-bank.az/en/x", Language.EN))
    documents.append(_doc("https://abb-bank.az/ru/x", Language.RU))

    # Act
    sample = select_sample(documents, 3)

    # Assert
    assert {doc.language for doc in sample} == {Language.AZ, Language.EN, Language.RU}


def test_select_sample_zero_limit_returns_empty() -> None:
    # Arrange & Act & Assert
    assert select_sample([_doc("https://abb-bank.az/p", Language.AZ)], 0) == []
