import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

from abb_contracts import CorpusDocument
from abb_rag import ExternalServiceError, get_logger
from playwright.async_api import BrowserContext, async_playwright
from structlog.typing import FilteringBoundLogger

from abb_scraper.config import ScraperSettings
from abb_scraper.exporters import write_corpus
from abb_scraper.extraction import compute_content_hash, extract_rendered
from abb_scraper.metadata import (
    derive_language,
    derive_segment,
    is_crawlable_url,
    is_noise,
    reconcile_language,
)

SITEMAP_PATH = "/sitemap.xml"
ROBOTS_PATH = "/robots.txt"
PAGE_WAIT_MS = 3000
GOTO_TIMEOUT_MS = 30000
DEFAULT_CONCURRENCY = 5
_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)


def parse_sitemap_locs(xml: str) -> list[str]:
    """URLs from a sitemap; nested sitemap-index entries (`.xml`) are skipped."""

    return [loc for loc in _LOC_RE.findall(xml) if not loc.lower().endswith(".xml")]


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


async def _load_robots(
    context: BrowserContext, start_url: str, logger: FilteringBoundLogger
) -> RobotFileParser | None:
    """Fetch robots.txt. Fail closed on a server error; 4xx means no rules."""

    robots_url = urljoin(start_url, ROBOTS_PATH)
    try:
        response = await context.request.get(robots_url, timeout=GOTO_TIMEOUT_MS)
    except Exception as error:
        raise ExternalServiceError(f"robots.txt fetch failed: {robots_url}") from error
    if response.status >= 500:
        raise ExternalServiceError(f"robots.txt unavailable ({response.status}): {robots_url}")
    if not response.ok:
        logger.warning("robots_absent", url=robots_url, status=response.status)
        return None
    parser = RobotFileParser()
    parser.parse((await response.text()).splitlines())
    return parser


async def _discover_urls(
    context: BrowserContext,
    settings: ScraperSettings,
    language: str | None,
    limit: int | None,
    logger: FilteringBoundLogger,
) -> tuple[list[str], float | None]:
    """Resolve the crawl frontier from the sitemap, filtered by robots and scope."""

    sitemap_url = urljoin(settings.start_url, SITEMAP_PATH)
    response = await context.request.get(sitemap_url, timeout=GOTO_TIMEOUT_MS)
    if not response.ok:
        raise ExternalServiceError(f"sitemap fetch failed ({response.status}): {sitemap_url}")
    urls = select_urls(parse_sitemap_locs(await response.text()), settings.domain, language)

    robots = await _load_robots(context, settings.start_url, logger)
    delay: float | None = None
    if robots is not None:
        urls = [url for url in urls if robots.can_fetch(settings.user_agent, url)]
        crawl_delay = robots.crawl_delay(settings.user_agent)
        delay = float(crawl_delay) if crawl_delay is not None else None

    if limit is not None:
        urls = urls[:limit]
    if not urls:
        raise ExternalServiceError(f"no crawlable URLs discovered (language={language})")
    return urls, delay


async def _render_one(
    context: BrowserContext, url: str, logger: FilteringBoundLogger
) -> CorpusDocument | None:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
        await page.wait_for_timeout(PAGE_WAIT_MS)
        content = extract_rendered(await page.content())
    except Exception as error:
        # One bad page (navigation, render, or extraction) must not abort the crawl.
        logger.warning("render_failed", url=url, error=str(error))
        return None
    finally:
        await page.close()

    if content is None:
        return None
    return CorpusDocument(
        url=url,
        language=reconcile_language(content.markdown, derive_language(url)),
        segment=derive_segment(url),
        title=content.title,
        markdown=content.markdown,
        content_hash=compute_content_hash(content.markdown),
        fetched_at=datetime.now(UTC),
    )


def _dedupe(
    results: list[CorpusDocument | None | BaseException], logger: FilteringBoundLogger
) -> list[CorpusDocument]:
    documents: list[CorpusDocument] = []
    seen: set[str] = set()
    for result in results:
        if isinstance(result, BaseException):
            logger.warning("render_worker_failed", error=str(result))
            continue
        if result is None or result.content_hash in seen:
            continue
        seen.add(result.content_hash)
        documents.append(result)
    return documents


async def render_corpus(
    language: str | None,
    out_path: Path,
    concurrency: int,
    limit: int | None,
) -> int:
    settings = ScraperSettings()
    logger = get_logger("scraper.render")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            context = await browser.new_context(user_agent=settings.user_agent)
            urls, delay = await _discover_urls(context, settings, language, limit, logger)
            logger.info("render_start", language=language, urls=len(urls), out=str(out_path))
            semaphore = asyncio.Semaphore(concurrency)

            async def worker(url: str) -> CorpusDocument | None:
                async with semaphore:
                    if delay:
                        await asyncio.sleep(delay)
                    return await _render_one(context, url, logger)

            results = await asyncio.gather(*(worker(url) for url in urls), return_exceptions=True)
        finally:
            await browser.close()

    documents = _dedupe(list(results), logger)
    if not documents:
        raise ExternalServiceError(f"crawl produced 0 documents (language={language})")
    write_corpus(out_path, documents, settings.domain)
    logger.info("render_written", path=str(out_path), documents=len(documents))
    return len(documents)
