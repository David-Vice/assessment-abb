from collections.abc import Sequence

from abb_contracts import CorpusDocument
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from abb_rag.models import Chunk

_SELECT_DOC = text("SELECT id, content_hash FROM documents WHERE url = :url")

_INSERT_DOC = text(
    "INSERT INTO documents (url, language, segment, title, content_hash, fetched_at) "
    "VALUES (:url, :language, :segment, :title, :content_hash, :fetched_at) "
    "RETURNING id"
)

_UPDATE_DOC = text(
    "UPDATE documents SET language = :language, segment = :segment, title = :title, "
    "content_hash = :content_hash, fetched_at = :fetched_at WHERE id = :id"
)

_DELETE_CHUNKS = text("DELETE FROM chunks WHERE document_id = :id")

# tsv is a GENERATED column — we insert `content` only and let Postgres derive it.
_INSERT_CHUNK = text(
    "INSERT INTO chunks "
    "(document_id, ordinal, content, language, segment, embedding, token_count) "
    "VALUES "
    "(:document_id, :ordinal, :content, :language, :segment, (:embedding)::halfvec, :token_count)"
)


async def load_existing_hashes(session: AsyncSession) -> dict[str, str]:
    """url → content_hash for every indexed document (drives idempotency)."""

    rows = (await session.execute(text("SELECT url, content_hash FROM documents"))).all()
    return {row.url: row.content_hash for row in rows}


async def upsert_document(
    session: AsyncSession,
    document: CorpusDocument,
    chunks: Sequence[Chunk],
    embeddings: Sequence[Sequence[float]],
) -> int:
    """Insert or replace a document and its chunks; no-op if the hash is unchanged."""

    existing = (await session.execute(_SELECT_DOC, {"url": document.url})).first()
    if existing is not None and existing.content_hash == document.content_hash:
        return int(existing.id)

    # A brand-new document with no chunks (e.g. all-boilerplate) would be an
    # unretrievable orphan row — skip it.
    if existing is None and not chunks:
        return 0

    if existing is None:
        document_id = int(
            (await session.execute(_INSERT_DOC, _document_params(document))).scalar_one()
        )
    else:
        document_id = int(existing.id)
        await session.execute(_UPDATE_DOC, {**_document_params(document), "id": document_id})
        await session.execute(_DELETE_CHUNKS, {"id": document_id})

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        await session.execute(_INSERT_CHUNK, _chunk_params(document_id, chunk, embedding))
    return document_id


def _document_params(document: CorpusDocument) -> dict[str, object]:
    return {
        "url": document.url,
        "language": document.language.value,
        "segment": document.segment.value,
        "title": document.title,
        "content_hash": document.content_hash,
        "fetched_at": document.fetched_at,
    }


def _chunk_params(document_id: int, chunk: Chunk, embedding: Sequence[float]) -> dict[str, object]:
    return {
        "document_id": document_id,
        "ordinal": chunk.ordinal,
        "content": chunk.content,
        "language": chunk.language.value,
        "segment": chunk.segment.value,
        "embedding": to_halfvec(embedding),
        "token_count": chunk.token_count,
    }


def to_halfvec(embedding: Sequence[float]) -> str:
    """Serialize a vector to a pgvector `halfvec` literal: `[v1,v2,...]`."""

    return "[" + ",".join(str(value) for value in embedding) + "]"
