from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from abb_contracts import CorpusDocument
from abb_rag import get_logger
from scrapy.exceptions import DropItem

from abb_scraper.exporters import write_corpus
from abb_scraper.extraction import compute_content_hash
from abb_scraper.metadata import derive_language, derive_segment


class CorpusPipeline:
    """Validates, dedupes (by content hash), and writes the corpus envelope."""

    def __init__(self) -> None:
        self._documents: list[CorpusDocument] = []
        self._seen_hashes: set[str] = set()
        self._logger = get_logger("scraper.pipeline")
        self._output_path = Path("corpus.json")
        self._source = "abb-bank.az"

    def open_spider(self, spider: Any) -> None:
        self._output_path = Path(spider.settings.get("CORPUS_OUTPUT_PATH", "corpus.json"))
        self._source = spider.settings.get("CORPUS_SOURCE", "abb-bank.az")

    def process_item(self, item: dict[str, Any], spider: Any) -> dict[str, Any]:
        url = item["url"]
        markdown = item["markdown"]
        content_hash = compute_content_hash(markdown)
        if content_hash in self._seen_hashes:
            raise DropItem(f"duplicate content: {url}")
        self._seen_hashes.add(content_hash)
        self._documents.append(
            CorpusDocument(
                url=url,
                language=derive_language(url),
                segment=derive_segment(url),
                title=item.get("title"),
                markdown=markdown,
                content_hash=content_hash,
                fetched_at=datetime.now(UTC),
            )
        )
        return item

    def close_spider(self, spider: Any) -> None:
        write_corpus(self._output_path, self._documents, self._source)
        self._logger.info(
            "corpus_written",
            path=str(self._output_path),
            documents=len(self._documents),
        )
