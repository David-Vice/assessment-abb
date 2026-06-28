import hashlib
import re
from dataclasses import dataclass

import trafilatura

# Pages below this many extracted characters are treated as nav/boilerplate-only.
MIN_CONTENT_CHARS = 200

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


def compute_content_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_title(html: str) -> str | None:
    match = _TITLE_RE.search(html)
    if match is None:
        return None
    title = _WHITESPACE_RE.sub(" ", match.group(1)).strip()
    return title or None
