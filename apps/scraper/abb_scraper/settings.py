from pathlib import Path
from typing import Any

from abb_scraper.config import ScraperSettings


def build_settings(
    *,
    config: ScraperSettings,
    max_pages: int,
    max_depth: int,
    playwright: bool,
    output_path: Path,
    source: str,
) -> dict[str, Any]:
    """Assemble Scrapy settings. Playwright handlers are wired only when enabled."""

    settings: dict[str, Any] = {
        "BOT_NAME": "abb_scraper",
        "USER_AGENT": config.user_agent,
        "ROBOTSTXT_OBEY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": config.download_delay,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        # Gentle on a bank's infrastructure (default ~1 concurrent; tunable for
        # a one-off full crawl via SCRAPE_TARGET_CONCURRENCY).
        "AUTOTHROTTLE_TARGET_CONCURRENCY": config.target_concurrency,
        "DOWNLOAD_DELAY": config.download_delay,
        "CONCURRENT_REQUESTS_PER_DOMAIN": config.concurrent_requests_per_domain,
        "DEPTH_LIMIT": max_depth,
        "CLOSESPIDER_PAGECOUNT": max_pages,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 2,
        # Each URL must serve its own language; a shared cookie jar lets the site
        # pin one language (set from the first page) across later requests.
        "COOKIES_ENABLED": False,
        "LOG_LEVEL": "INFO",
        "TELNETCONSOLE_ENABLED": False,
        "ITEM_PIPELINES": {"abb_scraper.pipelines.CorpusPipeline": 300},
        # Custom keys read by the pipeline at close.
        "CORPUS_OUTPUT_PATH": str(output_path),
        "CORPUS_SOURCE": source,
        "SCRAPE_PLAYWRIGHT_ENABLED": playwright,
    }
    if playwright:
        settings["DOWNLOAD_HANDLERS"] = {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        }
        settings["TWISTED_REACTOR"] = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
        settings["PLAYWRIGHT_BROWSER_TYPE"] = "chromium"
    return settings
