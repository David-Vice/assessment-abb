from datetime import UTC, datetime

from abb_contracts import CorpusDocument, Language, Segment
from abb_rag import get_logger
from abb_scraper.render import _dedupe, parse_sitemap_locs, select_urls


def _doc(content_hash: str) -> CorpusDocument:
    return CorpusDocument(
        url="https://abb-bank.az/x",
        language=Language.AZ,
        segment=Segment.OTHER,
        markdown="a body long enough for the corpus document",
        content_hash=content_hash,
        fetched_at=datetime.now(UTC),
    )


def test_parse_sitemap_locs_extracts_and_skips_nested_sitemaps() -> None:
    # Arrange
    xml = (
        "<urlset><url><loc> https://abb-bank.az/a </loc></url>"
        "<url><loc>https://abb-bank.az/b.xml</loc></url></urlset>"
    )

    # Act & Assert
    assert parse_sitemap_locs(xml) == ["https://abb-bank.az/a"]


def test_select_urls_filters_noise_assets_and_foreign_hosts_and_dedups() -> None:
    # Arrange
    urls = [
        "https://abb-bank.az/en/ferdi",
        "https://abb-bank.az/en/ferdi",
        "https://abb-bank.az/en/xeberler/article",
        "https://abb-bank.az/kampaniyalar/promo",
        "https://abb-bank.az/files/rates.pdf",
        "https://evil.com/phish",
    ]

    # Act & Assert
    assert select_urls(urls, "abb-bank.az", None) == ["https://abb-bank.az/en/ferdi"]


def test_select_urls_respects_language_scope() -> None:
    # Arrange
    urls = [
        "https://abb-bank.az/ferdi",
        "https://abb-bank.az/en/ferdi",
        "https://abb-bank.az/ru/ferdi",
    ]

    # Act & Assert
    assert select_urls(urls, "abb-bank.az", "en") == ["https://abb-bank.az/en/ferdi"]


def test_dedupe_skips_exceptions_none_and_duplicate_hashes() -> None:
    # Arrange — a worker exception and a None must be skipped, not abort the crawl.
    results: list[CorpusDocument | None | BaseException] = [
        _doc("sha256:1"),
        None,
        ValueError("one bad page"),
        _doc("sha256:1"),
        _doc("sha256:2"),
    ]

    # Act
    documents = _dedupe(results, get_logger("test"))

    # Assert
    assert [document.content_hash for document in documents] == ["sha256:1", "sha256:2"]
