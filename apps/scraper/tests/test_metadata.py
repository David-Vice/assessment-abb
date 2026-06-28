import pytest
from abb_contracts import Language, Segment
from abb_scraper.metadata import derive_language, derive_segment, is_crawlable_url, is_noise


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://abb-bank.az/", Language.AZ),
        ("https://abb-bank.az/ferdi/kartlar", Language.AZ),
        ("https://abb-bank.az/en/ferdi", Language.EN),
        ("https://abb-bank.az/ru/biznes", Language.RU),
    ],
)
def test_derive_language(url: str, expected: Language) -> None:
    # Arrange & Act & Assert
    assert derive_language(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://abb-bank.az/en/ferdi/cards", Segment.INDIVIDUALS),
        ("https://abb-bank.az/en/business/loans", Segment.BUSINESS),
        ("https://abb-bank.az/en/haqqimizda/missiya", Segment.ABOUT),
        ("https://abb-bank.az/en/news", Segment.OTHER),
    ],
)
def test_derive_segment(url: str, expected: Segment) -> None:
    # Arrange & Act & Assert
    assert derive_segment(url) == expected


def test_is_crawlable_accepts_same_domain_html() -> None:
    # Arrange & Act & Assert
    assert is_crawlable_url("https://abb-bank.az/en/ferdi", "abb-bank.az")
    assert is_crawlable_url("https://www.abb-bank.az/en/ferdi", "abb-bank.az")


def test_is_crawlable_rejects_assets_other_schemes_and_domains() -> None:
    # Arrange & Act & Assert
    assert not is_crawlable_url("https://abb-bank.az/files/rates.pdf", "abb-bank.az")
    assert not is_crawlable_url("mailto:info@abb-bank.az", "abb-bank.az")
    assert not is_crawlable_url("https://facebook.com/abbbank", "abb-bank.az")
    assert not is_crawlable_url("https://evil-abb-bank.az/phish", "abb-bank.az")
    # Portal subdomains (login-walled apps) are out of scope for the info corpus.
    assert not is_crawlable_url("https://prime.abb-bank.az/login", "abb-bank.az")


def test_is_noise_flags_news_and_procurement_only() -> None:
    # Arrange & Act & Assert
    assert is_noise("https://abb-bank.az/en/xeberler/some-article")
    assert is_noise("https://abb-bank.az/haqqimizda/satinalmalar/bildirisler")
    assert not is_noise("https://abb-bank.az/en/ferdi/kartlar/tam-visa")
    assert not is_noise("https://abb-bank.az/en/haqqimizda/rekvizitler")
