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

# The "rate this page / share your feedback" widget ABB injects site-wide in all
# three languages. It is not page content and leaks into ~40% of pages, so it is
# stripped before length checks (a page that is *only* the widget is then dropped).
_FEEDBACK_BOILERPLATE = (
    "Səhifəni dəyərləndirin",
    "Fikirlərinizi bizimlə bölüşün",
    "Rate the page",
    "Share your thoughts with us",
    "Оцените страницу",
    "Поделитесь с нами своими мыслями",
)
# Block-level tags whose text must be newline-separated; otherwise lxml's
# text_content() fuses adjacent blocks into run-on lines (mashed extraction).
_BLOCK_TAGS = frozenset(
    {
        "p", "div", "section", "article", "li", "ul", "ol", "table", "tr", "td",
        "th", "h1", "h2", "h3", "h4", "h5", "h6", "br", "blockquote", "dd", "dt",
    }
)

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


@dataclass(frozen=True, slots=True)
class ExtractedContent:
    title: str | None
    markdown: str


def extract_rendered(html: str) -> ExtractedContent | None:
    """Extract clean markdown from Playwright-rendered HTML.

    trafilatura handles prose pages cleanly, but discards structured tables
    (bank requisites, card spec tables). When it comes back thin, fall back to
    lxml visible-text (chrome stripped), which preserves those tables. The
    site-wide feedback widget is stripped from both paths. Returns None when
    there is no substantive content.
    """

    markdown = trafilatura.extract(
        html,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    prose = "" if markdown is None else clean_markdown(str(markdown))
    if len(prose) >= MIN_PROSE_CHARS:
        return ExtractedContent(title=_extract_title(html), markdown=prose)

    visible = clean_markdown(_visible_text(html))
    if len(visible) >= MIN_CONTENT_CHARS:
        return ExtractedContent(title=_extract_title(html), markdown=visible)
    return None


def clean_markdown(text: str) -> str:
    """Drop the site-wide feedback widget and collapse runs of blank lines."""

    kept = [
        line
        for line in text.splitlines()
        if not any(phrase in line for phrase in _FEEDBACK_BOILERPLATE)
    ]
    return _BLANK_LINES_RE.sub("\n\n", "\n".join(kept)).strip()


def compute_content_hash(text: str) -> str:
    """Hash whitespace-normalized text so trivial spacing variants dedupe."""

    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _visible_text(html: str) -> str:
    document = lxml_html.fromstring(html)
    for element in document.xpath("|".join(f"//{tag}" for tag in _CHROME_TAGS)):
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    # Inject newline boundaries around block elements before flattening, so their
    # text doesn't fuse into run-on lines (the cause of mashed extraction).
    for element in document.iter():
        if isinstance(element.tag, str) and element.tag in _BLOCK_TAGS:
            if element.text:
                element.text = "\n" + element.text
            element.tail = "\n" + (element.tail or "")
    lines = [line.strip() for line in document.text_content().splitlines() if line.strip()]
    return "\n".join(lines)


def _extract_title(html: str) -> str | None:
    match = _TITLE_RE.search(html)
    if match is None:
        return None
    title = _WHITESPACE_RE.sub(" ", match.group(1)).strip()
    return title or None
