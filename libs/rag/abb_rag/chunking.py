import re

import tiktoken
from abb_contracts import CorpusDocument

from abb_rag.models import Chunk

# text-embedding-3-* use the cl100k_base encoding.
_ENCODING = tiktoken.get_encoding("cl100k_base")
_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")

MAX_CHUNK_TOKENS = 1024
TARGET_CHUNK_TOKENS = 800
OVERLAP_TOKENS = 80
# Below this, a chunk is a stray heading/label (e.g. "ABB") — too small to embed
# meaningfully, so drop it rather than pollute retrieval.
MIN_CHUNK_TOKENS = 5


def chunk_document(document: CorpusDocument) -> list[Chunk]:
    """Split a document into token-budgeted chunks.

    Heading-aware: each chunk carries the full heading breadcrumb (e.g.
    "# Cards\n## Fees") so generic subsections keep their parent context. Short
    docs stay whole; long sections split into overlapping token windows;
    heading-only (empty-body) sections are skipped.
    """

    chunks: list[Chunk] = []
    for breadcrumb, body in _split_by_headings(document.markdown):
        body_text = body.strip()
        if not body_text:
            continue
        section = f"{breadcrumb}\n\n{body_text}" if breadcrumb else body_text
        for window in _token_windows(section):
            piece = (
                window
                if breadcrumb is None or window.startswith(breadcrumb)
                else f"{breadcrumb}\n\n{window}"
            )
            token_count = _count_tokens(piece)
            if token_count < MIN_CHUNK_TOKENS:
                continue
            chunks.append(
                Chunk(
                    url=document.url,
                    ordinal=len(chunks),
                    content=piece,
                    language=document.language,
                    segment=document.segment,
                    token_count=token_count,
                    title=document.title,
                )
            )
    return chunks


def count_tokens(text: str) -> int:
    """Token count under the embedding encoding (cl100k_base) — used for budgets."""

    return _count_tokens(text)


def _count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _split_by_headings(markdown: str) -> list[tuple[str | None, str]]:
    """Yield (breadcrumb, body) sections; breadcrumb is the full heading path."""

    sections: list[tuple[str | None, str]] = []
    stack: list[tuple[int, str]] = []
    breadcrumb: str | None = None
    body: list[str] = []

    def flush() -> None:
        if breadcrumb is not None or any(line.strip() for line in body):
            sections.append((breadcrumb, "\n".join(body)))

    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, line.strip()))
            breadcrumb = "\n".join(heading for _, heading in stack)
            body = []
        else:
            body.append(line)
    flush()
    return sections


def _token_windows(text: str) -> list[str]:
    tokens = _ENCODING.encode(text)
    if len(tokens) <= MAX_CHUNK_TOKENS:
        return [text]
    step = TARGET_CHUNK_TOKENS - OVERLAP_TOKENS
    windows: list[str] = []
    for start in range(0, len(tokens), step):
        window = tokens[start : start + TARGET_CHUNK_TOKENS]
        if not window:
            break
        windows.append(_ENCODING.decode(window))
        if start + TARGET_CHUNK_TOKENS >= len(tokens):
            break
    return windows
