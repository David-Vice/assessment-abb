import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from abb_contracts import CorpusDocument
from abb_rag import get_logger
from playwright.async_api import async_playwright

from abb_scraper.config import ScraperSettings
from abb_scraper.exporters import write_corpus
from abb_scraper.extraction import compute_content_hash, extract_rendered
from abb_scraper.metadata import derive_language, derive_segment, is_crawlable_url, is_noise

SITEMAP_PATH = "/sitemap.xml"
ROBOTS_PATH = "/robots.txt"
PAGE_WAIT_MS = 3000
GOTO_TIMEOUT_MS = 30000
DEFAULT_CONCURRENCY = 5


def parse_sitemap_locs(xml: str) -> list[str]:
    return [loc.strip() for loc in re.findall(r"<loc>(.*?)</loc>", xml) if not loc.endswith(".xml")]


async def _allowed_by_robots(
    context: Any, start_url: str, user_agent: str, urls: list[str], logger: Any
) -> list[str]:
    """Drop URLs disallowed by robots.txt. Politeness: we honor the bank's rules.

    If robots.txt is missing/unreadable, we proceed (sitemap URLs are crawl-sanctioned).
    """

    robots_url = urljoin(start_url, ROBOTS_PATH)
    try:
        response = await context.request.get(robots_url, timeout=GOTO_TIMEOUT_MS)
        if not response.ok:
            return urls
        parser = RobotFileParser()
        parser.parse((await response.text()).splitlines())
    except Exception as error:  # noqa: BLE001 - missing robots must not abort the crawl
        logger.warning("robots_unavailable", url=robots_url, error=str(error))
        return urls
    return [url for url in urls if parser.can_fetch(user_agent, url)]


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
        sitemap_url = urljoin(settings.start_url, SITEMAP_PATH)
        sitemap = await context.request.get(sitemap_url, timeout=GOTO_TIMEOUT_MS)
        urls = select_urls(parse_sitemap_locs(await sitemap.text()), domain, language)
        urls = await _allowed_by_robots(
            context, settings.start_url, settings.user_agent, urls, logger
        )
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
