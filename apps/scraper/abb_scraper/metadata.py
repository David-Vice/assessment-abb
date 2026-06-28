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


def _path_of(url: str) -> str:
    return urlparse(url).path


def derive_language(url: str) -> Language:
    """ABB serves EN under /en/ and RU under /ru/; the root is Azerbaijani."""

    first_segment = _path_of(url).lstrip("/").split("/", 1)[0].lower()
    if first_segment == "en":
        return Language.EN
    if first_segment == "ru":
        return Language.RU
    return Language.AZ


def derive_segment(url: str) -> Segment:
    path = _path_of(url).lower()
    if "ferdi" in path or "individual" in path:
        return Segment.INDIVIDUALS
    if "biznes" in path or "business" in path:
        return Segment.BUSINESS
    if "haqqimizda" in path or "about" in path:
        return Segment.ABOUT
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
