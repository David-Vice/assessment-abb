import argparse
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from abb_rag import configure_logging, get_logger
from scrapy.crawler import CrawlerProcess

from abb_scraper.config import ScraperSettings
from abb_scraper.exporters import load_corpus, merge_corpora, write_corpus
from abb_scraper.sample import select_sample
from abb_scraper.settings import build_settings
from abb_scraper.spiders.abb import AbbSpider

DEFAULT_SAMPLE_SIZE = 25


def main() -> None:
    args = _parse_args()
    configure_logging()
    logger = get_logger("scraper.cli")

    if args.merge:
        _run_merge(args, logger)
        return

    config = ScraperSettings()
    language_roots = {"az": "/", "en": "/en/", "ru": "/ru/"}
    if args.start_url:
        start_url = args.start_url
    elif args.only_language:
        start_url = urljoin(config.start_url, language_roots[args.only_language])
    else:
        start_url = config.start_url
    max_pages = args.max_pages or config.max_pages
    max_depth = config.max_depth if args.max_depth is None else args.max_depth
    playwright = args.playwright or config.playwright_enabled
    output_path = Path(args.out)
    source = urlparse(start_url).netloc

    logger.info(
        "scrape_start",
        start_url=start_url,
        max_pages=max_pages,
        max_depth=max_depth,
        playwright=playwright,
        only_language=args.only_language,
        out=str(output_path),
    )

    settings = build_settings(
        config=config,
        max_pages=max_pages,
        max_depth=max_depth,
        playwright=playwright,
        output_path=output_path,
        source=source,
    )
    process = CrawlerProcess(settings)
    process.crawl(AbbSpider, start_url=start_url, only_language=args.only_language)
    process.start()

    if args.sample:
        _write_sample(output_path, args.sample_size, logger)


def _run_merge(args: argparse.Namespace, logger: Any) -> None:
    output_path = Path(args.out)
    inputs = [Path(p) for p in args.merge]
    count = merge_corpora(inputs, output_path, source="abb-bank.az")
    logger.info("merge_written", path=str(output_path), documents=count)
    if args.sample:
        _write_sample(output_path, args.sample_size, logger)


def _write_sample(corpus_path: Path, sample_size: int, logger: Any) -> None:
    corpus = load_corpus(corpus_path)
    sampled = select_sample(corpus.documents, sample_size)
    sample_path = corpus_path.with_name("corpus.sample.json")
    write_corpus(sample_path, sampled, corpus.source)
    logger.info("sample_written", path=str(sample_path), documents=len(sampled))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="abb-scrape",
        description="Crawl the ABB website into a corpus.json for the RAG pipeline.",
    )
    parser.add_argument("--out", default="corpus.json", help="Output path (default: corpus.json)")
    parser.add_argument("--start-url", default=None, help="Override the crawl start URL")
    parser.add_argument(
        "--only-language",
        choices=["az", "en", "ru"],
        default=None,
        help="Restrict the crawl to one language tree (for balanced multi-pass corpora)",
    )
    parser.add_argument("--max-pages", type=int, default=None, help="Stop after N pages")
    parser.add_argument("--max-depth", type=int, default=None, help="Max crawl depth")
    parser.add_argument(
        "--playwright",
        action="store_true",
        help="Enable headless-browser fallback for JS-rendered pages",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Also write a trimmed corpus.sample.json",
    )
    parser.add_argument(
        "--merge",
        nargs="+",
        metavar="CORPUS",
        default=None,
        help="Merge the given corpus files into --out (dedup by content hash) and exit",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Documents in the sample (default: {DEFAULT_SAMPLE_SIZE})",
    )
    return parser.parse_args()
