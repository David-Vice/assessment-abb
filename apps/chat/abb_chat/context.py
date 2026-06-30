from abb_contracts import Citation
from abb_rag import RetrievedChunk, count_tokens

CITATION_SNIPPET_CHARS = 240


def build_context(chunks: list[RetrievedChunk], token_budget: int) -> str:
    """Pack ranked chunks into a delimited context string within a token budget."""

    blocks: list[str] = []
    used = 0
    for index, chunk in enumerate(chunks, start=1):
        block = f"[Source {index}] URL: {chunk.url}\n{chunk.content}"
        tokens = count_tokens(block)
        if blocks and used + tokens > token_budget:
            break
        blocks.append(block)
        used += tokens
    return "\n\n---\n\n".join(blocks)


def to_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """One citation per source URL (retrieval returns several chunks per page)."""

    seen: set[str] = set()
    citations: list[Citation] = []
    for chunk in chunks:
        if chunk.url in seen:
            continue
        seen.add(chunk.url)
        citations.append(
            Citation(
                url=chunk.url,
                title=chunk.title,
                language=chunk.language,
                segment=chunk.segment,
                snippet=_snippet(chunk.content),
            )
        )
    return citations


def _snippet(content: str) -> str:
    return " ".join(content.split())[:CITATION_SNIPPET_CHARS]
