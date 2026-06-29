"""End-to-end smoke check for the RAG core (libs/rag).

Ingests the sample corpus, proves idempotency, then runs multilingual
retrieval. Requires the docker Postgres up and a real OPENAI_API_KEY.

  DATABASE_URL=postgresql+psycopg://abb:abb@localhost:5432/abb_rag \
  RERANK_ENABLED=false uv run python scripts/verify_rag.py

Drop RERANK_ENABLED to also exercise the cross-encoder (downloads the model
on first run).
"""

import asyncio
import sys
from pathlib import Path

from abb_contracts import Corpus, Language
from abb_rag import ingest_corpus, retrieve, session_scope

if sys.platform == "win32":
    # psycopg async requires a Selector loop; Proactor is the Windows default.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # Windows consoles default to cp1252; force UTF-8 so AZ/RU output prints.
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

CORPUS_PATH = Path("corpus.sample.json")
PREVIEW_CHARS = 90
QUERIES: list[tuple[str, Language]] = [
    ("How can I get a credit card from ABB?", Language.EN),
    ("ABB bank rekvizitləri və SWIFT kodu", Language.AZ),
    ("реквизиты банка ABB", Language.RU),
]


async def run(corpus: Corpus) -> None:
    indexed = await ingest_corpus(corpus)
    print(f"indexed chunks: {indexed}")

    reindexed = await ingest_corpus(corpus)
    print(f"re-ingest chunks (idempotency, expect 0): {reindexed}")

    for question, language in QUERIES:
        async with session_scope() as session:
            hits = await retrieve(session, question, language)
        print(f"\nQ[{language.value}]: {question}  -> {len(hits)} hits")
        for hit in hits:
            preview = " ".join(hit.content.split())[:PREVIEW_CHARS]
            print(f"  {hit.score:.4f} [{hit.language.value}] {hit.url}")
            print(f"         {preview!r}")


def main() -> None:
    corpus = Corpus.model_validate_json(CORPUS_PATH.read_text(encoding="utf-8"))
    print(f"corpus: {len(corpus.documents)} docs from {corpus.source}")
    asyncio.run(run(corpus))


if __name__ == "__main__":
    main()
