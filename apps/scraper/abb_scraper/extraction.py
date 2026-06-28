import hashlib
import re
from dataclasses import dataclass

import trafilatura
from lxml import html as lxml_html

# Pages below this many extracted characters are treated as nav/boilerplate-only.
MIN_CONTENT_CHARS = 200
# trafilatura strips structured tables (e.g. the requisites page) as boilerplate.
# When it returns less than this, fall back to lxml visible-text on rendered HTML.
MIN_PROSE_CHARS = 400
_CHROME_TAGS = ("script", "style", "nav", "header", "footer", "noscript", "svg")

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class ExtractedContent:
    title: str | None
    markdown: str


def extract_content(html: str) -> ExtractedContent | None:
    """Extract clean markdown from a page; None if there's no substantive content."""

    markdown = trafilatura.extract(
        html,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
    )
    if markdown is None:
        return None
    text = str(markdown).strip()
    if len(text) < MIN_CONTENT_CHARS:
        return None
    return ExtractedContent(title=_extract_title(html), markdown=text)


def extract_rendered(html: str) -> ExtractedContent | None:
    """Extract from Playwright-rendered HTML.

    trafilatura handles prose pages cleanly, but discards structured tables
    (bank requisites, card spec tables). When it comes back thin, fall back to
    lxml visible-text (chrome stripped), which preserves those tables.
    """

    markdown = trafilatura.extract(
        html,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    prose = "" if markdown is None else str(markdown).strip()
    if len(prose) >= MIN_PROSE_CHARS:
        return ExtractedContent(title=_extract_title(html), markdown=prose)

    visible = _visible_text(html)
    if len(visible) >= MIN_CONTENT_CHARS:
        return ExtractedContent(title=_extract_title(html), markdown=visible)
    return None


def compute_content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _visible_text(html: str) -> str:
    document = lxml_html.fromstring(html)
    for element in document.xpath("|".join(f"//{tag}" for tag in _CHROME_TAGS)):
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    lines = [line.strip() for line in document.text_content().splitlines() if line.strip()]
    return "\n".join(lines)


def _extract_title(html: str) -> str | None:
    match = _TITLE_RE.search(html)
    if match is None:
        return None
    title = _WHITESPACE_RE.sub(" ", match.group(1)).strip()
    return title or None
