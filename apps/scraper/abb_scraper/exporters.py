from datetime import UTC, datetime
from pathlib import Path

from abb_contracts import Corpus, CorpusDocument


def write_corpus(path: Path, documents: list[CorpusDocument], source: str) -> None:
    """Write the corpus envelope, sorted by URL for stable, reviewable diffs."""

    corpus = Corpus(
        source=source,
        generated_at=datetime.now(UTC),
        documents=sorted(documents, key=lambda document: document.url),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(corpus.model_dump_json(indent=2), encoding="utf-8")


def load_corpus(path: Path) -> Corpus:
    return Corpus.model_validate_json(path.read_text(encoding="utf-8"))


def merge_corpora(inputs: list[Path], output: Path, source: str) -> int:
    """Merge per-language corpora into one, de-duplicating by content hash.

    Used to assemble a balanced multilingual corpus from separate `--only-language`
    passes (the site interlinks languages unevenly, so one crawl skews by language).
    Returns the merged document count.
    """

    documents: list[CorpusDocument] = []
    seen: set[str] = set()
    for path in inputs:
        for document in load_corpus(path).documents:
            if document.content_hash in seen:
                continue
            seen.add(document.content_hash)
            documents.append(document)
    write_corpus(output, documents, source)
    return len(documents)
