import argparse
import asyncio
from pathlib import Path
from typing import Any

from abb_rag import configure_logging, get_logger

from abb_scraper.exporters import load_corpus, merge_corpora, write_corpus
from abb_scraper.render import DEFAULT_CONCURRENCY, render_corpus
from abb_scraper.sample import select_sample

DEFAULT_SAMPLE_SIZE = 25
DEFAULT_SOURCE = "abb-bank.az"


def main() -> None:
    args = _parse_args()
    configure_logging()
    logger = get_logger("scraper.cli")

    if args.merge:
        _run_merge(args, logger)
        return

    output_path = Path(args.out)
    logger.info(
        "scrape_start",
        only_language=args.only_language,
        concurrency=args.concurrency,
        limit=args.limit,
        out=str(output_path),
    )
    asyncio.run(
        render_corpus(
            language=args.only_language,
            out_path=output_path,
            concurrency=args.concurrency,
            limit=args.limit,
        )
    )

    if args.sample:
        _write_sample(output_path, args.sample_size, logger)


def _run_merge(args: argparse.Namespace, logger: Any) -> None:
    output_path = Path(args.out)
    inputs = [Path(p) for p in args.merge]
    count = merge_corpora(inputs, output_path, source=DEFAULT_SOURCE)
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
        description="Crawl the ABB website into a corpus.json for the RAG pipeline. "
        "Drives a headless browser over the sitemap (captures JS-rendered content "
        "like requisites/card tables) and excludes news/procurement noise.",
    )
    parser.add_argument("--out", default="corpus.json", help="Output path (default: corpus.json)")
    parser.add_argument(
        "--only-language",
        choices=["az", "en", "ru"],
        default=None,
        help="Restrict the crawl to one language tree (for balanced multi-pass corpora)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrent browser pages (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument("--limit", type=int, default=None, help="Crawl at most N pages (testing)")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Also write a trimmed corpus.sample.json",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Documents in the sample (default: {DEFAULT_SAMPLE_SIZE})",
    )
    parser.add_argument(
        "--merge",
        nargs="+",
        metavar="CORPUS",
        default=None,
        help="Merge the given corpus files into --out (dedup by content hash) and exit",
    )
    return parser.parse_args()
