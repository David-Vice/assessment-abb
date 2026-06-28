import argparse
import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from abb_contracts import CorpusDocument
from abb_rag import configure_logging, get_logger
from playwright.async_api import async_playwright

from abb_scraper.config import ScraperSettings
from abb_scraper.exporters import write_corpus
from abb_scraper.extraction import compute_content_hash, extract_rendered
from abb_scraper.metadata import derive_language, derive_segment, is_crawlable_url, is_noise

SITEMAP_URL = "https://abb-bank.az/sitemap.xml"
PAGE_WAIT_MS = 3000
GOTO_TIMEOUT_MS = 30000
DEFAULT_CONCURRENCY = 5


def parse_sitemap_locs(xml: str) -> list[str]:
    return [loc.strip() for loc in re.findall(r"<loc>(.*?)</loc>", xml) if not loc.endswith(".xml")]


def select_urls(urls: list[str], domain: str, language: str | None) -> list[str]:
    """Keep crawlable, non-noise, in-language page URLs (deduplicated, ordered)."""

    seen: set[str] = set()
    selected: list[str] = []
    for url in urls:
        if not url or url in seen:
            continue
        if not is_crawlable_url(url, domain) or is_noise(url):
            continue
        if language and derive_language(url).value != language:
            continue
        seen.add(url)
        selected.append(url)
    return selected


async def _render_one(context: Any, url: str, logger: Any) -> CorpusDocument | None:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
        await page.wait_for_timeout(PAGE_WAIT_MS)
        html: str = await page.content()
    except Exception as error:  # noqa: BLE001 - one bad page must not abort the crawl
        logger.warning("render_failed", url=url, error=str(error))
        return None
    finally:
        await page.close()

    content = extract_rendered(html)
    if content is None:
        return None
    return CorpusDocument(
        url=url,
        language=derive_language(url),
        segment=derive_segment(url),
        title=content.title,
        markdown=content.markdown,
        content_hash=compute_content_hash(content.markdown),
        fetched_at=datetime.now(UTC),
    )


async def render_corpus(
    language: str | None,
    out_path: Path,
    concurrency: int,
    limit: int | None,
) -> int:
    settings = ScraperSettings()
    logger = get_logger("scraper.render")
    domain = urlparse(settings.start_url).netloc
    semaphore = asyncio.Semaphore(concurrency)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context(user_agent=settings.user_agent)
        sitemap = await context.request.get(SITEMAP_URL, timeout=GOTO_TIMEOUT_MS)
        urls = select_urls(parse_sitemap_locs(await sitemap.text()), domain, language)
        if limit is not None:
            urls = urls[:limit]
        logger.info("render_start", language=language, urls=len(urls), out=str(out_path))

        async def worker(url: str) -> CorpusDocument | None:
            async with semaphore:
                return await _render_one(context, url, logger)

        results = await asyncio.gather(*(worker(url) for url in urls))
        await browser.close()

    documents: list[CorpusDocument] = []
    seen_hashes: set[str] = set()
    for document in results:
        if document is None or document.content_hash in seen_hashes:
            continue
        seen_hashes.add(document.content_hash)
        documents.append(document)
    write_corpus(out_path, documents, domain)
    logger.info("render_written", path=str(out_path), documents=len(documents))
    return len(documents)


def main() -> None:
    args = _parse_args()
    configure_logging()
    asyncio.run(render_corpus(args.only_language, Path(args.out), args.concurrency, args.limit))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="abb-render",
        description="Render ABB sitemap pages with a headless browser (captures JS-rendered "
        "content like requisites/cards); excludes news/procurement noise.",
    )
    parser.add_argument("--out", default="corpus.json", help="Output path")
    parser.add_argument(
        "--only-language",
        choices=["az", "en", "ru"],
        default=None,
        help="Render only one language tree (for parallel per-language runs)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Concurrent browser pages (default {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument("--limit", type=int, default=None, help="Render at most N pages (testing)")
    return parser.parse_args()
