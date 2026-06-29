import hashlib
import re
from dataclasses import dataclass
from html import unescape

import trafilatura
from lxml import html as lxml_html
from lxml.etree import ParserError

# Pages below this many extracted characters are treated as nav/boilerplate-only.
MIN_CONTENT_CHARS = 200
# Prefer clean trafilatura prose; use lxml visible-text only when it recovers
# substantially more content (structured tables trafilatura discards).
_VISIBLE_GAIN_RATIO = 1.5
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
# Block-level tags get newline separators; everything else gets a space, so that
# neither block runs (mashed paragraphs) nor inline runs (label↔value such as
# "ödənişi888.49") fuse when the tree is flattened to text.
_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "section",
        "article",
        "li",
        "ul",
        "ol",
        "table",
        "tr",
        "td",
        "th",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "br",
        "blockquote",
        "dd",
        "dt",
    }
)

# Heading tags are promoted to markdown so downstream chunking stays structure-aware.
_HEADING_TAGS = {
    "h1": "# ",
    "h2": "## ",
    "h3": "### ",
    "h4": "#### ",
    "h5": "##### ",
    "h6": "###### ",
}
# ABB serves a non-informative default <title> site-wide; fall back to the <h1>.
_GENERIC_TITLES = {"abb", "abb bank"}
# Drop exact-duplicate lines at least this long within a page (carousel/slider
# re-renders), keeping the first; shorter repeats (prices, bullets) are left alone.
_DEDUP_MIN_LINE = 40

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


@dataclass(frozen=True, slots=True)
class ExtractedContent:
    title: str | None
    markdown: str


def extract_rendered(html: str) -> ExtractedContent | None:
    """Extract clean markdown from Playwright-rendered HTML.

    trafilatura handles prose pages cleanly but discards structured tables (bank
    requisites, card spec tables); the lxml visible-text fallback recovers them.
    We keep whichever yields more content (the fallback only wins when it
    recovers substantially more), strip the site-wide feedback widget from both,
    and return None when there is no substantive content.
    """

    markdown = trafilatura.extract(
        html,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    prose = "" if markdown is None else clean_markdown(str(markdown))
    visible = clean_markdown(_visible_text(html))
    best = visible if len(visible) > len(prose) * _VISIBLE_GAIN_RATIO else prose
    if len(best) < MIN_CONTENT_CHARS:
        return None
    return ExtractedContent(title=_extract_title(html), markdown=best)


def clean_markdown(text: str) -> str:
    """Strip the feedback widget, drop intra-page duplicate lines, tidy blanks."""

    seen: set[str] = set()
    kept: list[str] = []
    for line in text.splitlines():
        if any(phrase in line for phrase in _FEEDBACK_BOILERPLATE):
            continue
        stripped = line.strip()
        if len(stripped) >= _DEDUP_MIN_LINE:
            if stripped in seen:
                continue
            seen.add(stripped)
        kept.append(line)
    return _BLANK_LINES_RE.sub("\n\n", "\n".join(kept)).strip()


def compute_content_hash(text: str) -> str:
    """Hash whitespace-normalized text so trivial spacing variants dedupe."""

    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _visible_text(html: str) -> str:
    try:
        document = lxml_html.fromstring(html)
    except ParserError:
        return ""
    for element in document.xpath("|".join(f"//{tag}" for tag in _CHROME_TAGS)):
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)
    # Inject separators around every element before text_content() flattens the
    # tree: newlines (with a markdown prefix for headings) between blocks, spaces
    # between inline elements.
    for element in document.iter():
        if not isinstance(element.tag, str):
            continue
        is_block = element.tag in _BLOCK_TAGS
        text_lead = "\n" + _HEADING_TAGS.get(element.tag, "") if is_block else " "
        if element.text:
            element.text = text_lead + element.text
        if element.tail:
            element.tail = ("\n" if is_block else " ") + element.tail
    lines = (" ".join(line.split()) for line in document.text_content().splitlines())
    return "\n".join(line for line in lines if line)


def _extract_title(html: str) -> str | None:
    match = _TITLE_RE.search(html)
    title = _WHITESPACE_RE.sub(" ", unescape(match.group(1))).strip() if match else ""
    if not title or title.lower() in _GENERIC_TITLES:
        heading = _first_heading(html)
        if heading:
            return heading
    return title or None


def _first_heading(html: str) -> str | None:
    try:
        document = lxml_html.fromstring(html)
    except ParserError:
        return None
    for node in document.xpath("//h1"):
        text = _WHITESPACE_RE.sub(" ", node.text_content()).strip()
        if text:
            return text
    return None
