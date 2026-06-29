from urllib.parse import urlparse

from abb_contracts import Language, Segment

# Non-textual resources we never want in a text corpus.
ASSET_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".bmp",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".rss",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".webm",
    ".mp3",
    ".wav",
    ".avi",
    ".mov",
)


# Sitemap sections excluded as noise for a customer Q&A corpus:
# - xeberler:     news articles (thousands, time-sensitive, low Q&A value)
# - satinalmalar: procurement/tender notices under /haqqimizda (internal, not customer info)
# - kampaniyalar: marketing campaigns — time-sensitive offers that expire (stale-answer
#   risk for "current offers" questions) and frequently left untranslated (their /en/ and
#   /ru/ URLs serve Azerbaijani text → language mislabeling). Excluded for the same
#   reasons as news and the procurement "about" pages.
NOISE_PATTERNS = ("xeberler", "satinalmalar", "kampaniyalar")


def _path_of(url: str) -> str:
    return urlparse(url).path


def is_noise(url: str) -> bool:
    path = _path_of(url).lower()
    return any(pattern in path for pattern in NOISE_PATTERNS)


def derive_language(url: str) -> Language:
    """ABB serves EN under /en/ and RU under /ru/; the root is Azerbaijani."""

    first_segment = _path_of(url).lstrip("/").split("/", 1)[0].lower()
    if first_segment == "en":
        return Language.EN
    if first_segment == "ru":
        return Language.RU
    return Language.AZ


# Authoritative site sections (URL prefixes). Business is checked first: a
# "biznes-krediti" page is a business product even though it also matches the
# retail "kredit" keyword below.
_BUSINESS_TOKENS = ("biznes", "business", "sahibkar", "korporativ")
_INDIVIDUAL_TOKENS = ("ferdi", "individual")
_ABOUT_TOKENS = ("haqqimizda", "about")
# Retail product keywords for root-level SEO landing pages that lack a /ferdi/
# section prefix (e.g. /100-manat-kredit, /kredit-kartlari, /emanet). Without
# these, ~60% of pages collapse to `other`; these recover the consumer products.
_RETAIL_KEYWORDS = (
    "kredit", "credit", "kart", "card", "əmanət", "emanet", "depozit",
    "deposit", "hesab", "account", "ipoteka", "mortgage", "pul-gonder", "transfer",
)


def derive_segment(url: str) -> Segment:
    """Classify a page by audience. URL sections win; root SEO pages fall back to
    retail-product keywords; everything else is `other`.

    Note: segment is display/analytics metadata (citation badges, the analytics
    segment-mix chart), not a retrieval filter — a miss never breaks answers.
    """

    path = _path_of(url).lower()
    if any(token in path for token in _BUSINESS_TOKENS):
        return Segment.BUSINESS
    if any(token in path for token in _INDIVIDUAL_TOKENS):
        return Segment.INDIVIDUALS
    if any(token in path for token in _ABOUT_TOKENS):
        return Segment.ABOUT
    if any(keyword in path for keyword in _RETAIL_KEYWORDS):
        return Segment.INDIVIDUALS
    return Segment.OTHER


def is_crawlable_url(url: str, allowed_domain: str) -> bool:
    """Same-domain HTTP(S) pages only; assets and other schemes are skipped."""

    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    # Apex + www only: keep the public info site, skip portals like prime.* / online.*
    host = parsed.netloc.lower()
    if host not in (allowed_domain, f"www.{allowed_domain}"):
        return False
    path = parsed.path.lower()
    return not any(path.endswith(ext) for ext in ASSET_EXTENSIONS)
