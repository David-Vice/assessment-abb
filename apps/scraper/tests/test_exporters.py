from datetime import UTC, datetime
from pathlib import Path

from abb_contracts import CorpusDocument, Language, Segment
from abb_scraper.exporters import load_corpus, merge_corpora, write_corpus


def _doc(url: str, content_hash: str | None = None) -> CorpusDocument:
    return CorpusDocument(
        url=url,
        language=Language.EN,
        segment=Segment.INDIVIDUALS,
        markdown="a sufficiently long body of content for the corpus",
        content_hash=content_hash or f"sha256:{url}",
        fetched_at=datetime.now(UTC),
    )


def test_write_corpus_sorts_by_url_and_roundtrips(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "corpus.json"
    documents = [_doc("https://abb-bank.az/b"), _doc("https://abb-bank.az/a")]

    # Act
    write_corpus(path, documents, source="abb-bank.az")
    loaded = load_corpus(path)

    # Assert
    assert loaded.source == "abb-bank.az"
    assert [doc.url for doc in loaded.documents] == [
        "https://abb-bank.az/a",
        "https://abb-bank.az/b",
    ]


def test_write_corpus_creates_parent_directories(tmp_path: Path) -> None:
    # Arrange
    path = tmp_path / "nested" / "dir" / "corpus.json"

    # Act
    write_corpus(path, [_doc("https://abb-bank.az/a")], source="abb-bank.az")

    # Assert
    assert path.exists()


def test_merge_corpora_dedups_by_content_hash(tmp_path: Path) -> None:
    # Arrange — two files sharing one identical-content document.
    write_corpus(
        tmp_path / "a.json",
        [_doc("https://abb-bank.az/a", "sha256:shared")],
        "abb-bank.az",
    )
    write_corpus(
        tmp_path / "b.json",
        [_doc("https://abb-bank.az/b", "sha256:shared"), _doc("https://abb-bank.az/c", "sha256:c")],
        "abb-bank.az",
    )
    out = tmp_path / "merged.json"

    # Act
    count = merge_corpora([tmp_path / "a.json", tmp_path / "b.json"], out, source="abb-bank.az")

    # Assert
    assert count == 2
    assert {d.content_hash for d in load_corpus(out).documents} == {"sha256:shared", "sha256:c"}
