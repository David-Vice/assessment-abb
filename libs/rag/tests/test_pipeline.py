import contextlib
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from abb_contracts import Corpus, CorpusDocument, Language, Segment
from abb_rag import pipeline as pipeline_module
from abb_rag.models import Chunk
from abb_rag.pipeline import ingest_corpus


def _doc(url: str, content_hash: str) -> CorpusDocument:
    return CorpusDocument(
        url=url,
        language=Language.EN,
        segment=Segment.OTHER,
        title="T",
        markdown="This is a sufficiently long body to form exactly one chunk.",
        content_hash=content_hash,
        fetched_at=datetime.now(UTC),
    )


def _corpus(documents: list[CorpusDocument]) -> Corpus:
    return Corpus(source="abb-bank.az", generated_at=datetime.now(UTC), documents=documents)


@contextlib.asynccontextmanager
async def _fake_scope() -> AsyncIterator[object]:
    yield object()


async def test_ingest_corpus_embeds_and_indexes_with_aligned_slices(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    corpus = _corpus(
        [_doc("https://abb-bank.az/a", "sha256:a"), _doc("https://abb-bank.az/b", "sha256:b")]
    )
    upserts: list[tuple[str, int, int]] = []

    async def fake_hashes(session: Any) -> dict[str, str]:
        return {}

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.1] * 4 for _ in texts]

    async def fake_upsert(
        session: Any, document: CorpusDocument, chunks: Sequence[Chunk], embeddings: Sequence[Any]
    ) -> int:
        upserts.append((document.url, len(chunks), len(list(embeddings))))
        return 1

    monkeypatch.setattr(pipeline_module, "session_scope", _fake_scope)
    monkeypatch.setattr(pipeline_module, "load_existing_hashes", fake_hashes)
    monkeypatch.setattr(pipeline_module, "embed_texts", fake_embed)
    monkeypatch.setattr(pipeline_module, "upsert_document", fake_upsert)

    # Act
    indexed = await ingest_corpus(corpus)

    # Assert — one chunk per short doc; per-doc chunk/embedding slices align.
    assert indexed == 2
    assert [url for url, _, _ in upserts] == ["https://abb-bank.az/a", "https://abb-bank.az/b"]
    assert all(n_chunks == n_emb for _, n_chunks, n_emb in upserts)


async def test_ingest_corpus_is_idempotent_when_hashes_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    corpus = _corpus([_doc("https://abb-bank.az/a", "sha256:a")])
    embed_calls = 0

    async def fake_hashes(session: Any) -> dict[str, str]:
        return {"https://abb-bank.az/a": "sha256:a"}

    async def fake_embed(texts: list[str]) -> list[list[float]]:
        nonlocal embed_calls
        embed_calls += 1
        return []

    monkeypatch.setattr(pipeline_module, "session_scope", _fake_scope)
    monkeypatch.setattr(pipeline_module, "load_existing_hashes", fake_hashes)
    monkeypatch.setattr(pipeline_module, "embed_texts", fake_embed)

    # Act
    indexed = await ingest_corpus(corpus)

    # Assert — unchanged doc → nothing indexed and no embedding call.
    assert indexed == 0
    assert embed_calls == 0
