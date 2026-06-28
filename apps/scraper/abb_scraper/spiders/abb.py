import re
from collections.abc import AsyncIterator, Iterator
from typing import Any
from urllib.parse import urljoin, urlparse

import scrapy

from abb_scraper.config import DEFAULT_START_URL
from abb_scraper.extraction import extract_content
from abb_scraper.metadata import derive_language, is_crawlable_url

# ABB embeds navigation (incl. the /ru/ and /en/ trees) as quoted URL strings in
# script/JSON blobs, not just <a href> tags. Anchor-only extraction misses whole
# language sections, so we also harvest quoted same-site paths from the raw HTML.
_QUOTED_URL_RE = re.compile(
    r"""["'](/[A-Za-z0-9][^"'\\ <>]*|https?://[^"'\\ <>]*abb-bank\.az[^"'\\ <>]*)["']"""
)


class AbbSpider(scrapy.Spider):
    """Sitemap-seeded crawl over the ABB website.

    Content is mostly server-rendered, so pages are fetched over plain HTTP.
    When a page yields too little text and Playwright is enabled, the same URL is
    re-fetched with a headless browser (the only-when-needed fallback).
    """

    name = "abb"

    def __init__(
        self,
        start_url: str = DEFAULT_START_URL,
        only_language: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.start_url = start_url
        # When set, the crawl stays within one language tree (az|en|ru). Used to
        # build a balanced multilingual corpus from separate scoped passes — the
        # site interlinks languages unevenly, so a single crawl skews by language.
        self.only_language = only_language
        self.allowed_domains = [urlparse(start_url).netloc]

    async def start(self) -> AsyncIterator[Any]:
        robots_url = urljoin(self.start_url, "/robots.txt")
        # Scoped crawls rely purely on in-language HTML link-following: the sitemap
        # mixes languages (and is /haqqimizda-heavy), so seeding it would leak
        # out-of-scope pages. Unscoped crawls use sitemap + robots for coverage.
        if self.only_language is not None:
            seeds = [self.start_url]
        else:
            seeds = [
                robots_url,
                self.start_url,
                urljoin(self.start_url, "/en/"),
                urljoin(self.start_url, "/ru/"),
                urljoin(self.start_url, "/sitemap.xml"),
            ]
        seen: set[str] = set()
        for url in seeds:
            if url in seen:
                continue
            seen.add(url)
            callback = self._parse_robots if url == robots_url else self.parse
            yield scrapy.Request(url, callback=callback, dont_filter=True)

    def _parse_robots(self, response: Any) -> Iterator[Any]:
        """Discover sitemaps declared via the robots.txt `Sitemap:` directive."""

        for line in response.text.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("sitemap:"):
                sitemap_url = stripped.split(":", 1)[1].strip()
                if sitemap_url:
                    yield scrapy.Request(sitemap_url, callback=self.parse)

    def parse(self, response: Any) -> Iterator[Any]:
        if self._is_sitemap(response):
            yield from self._parse_sitemap(response)
            return

        content = extract_content(response.text)
        if content is None:
            if self._playwright_enabled() and not response.meta.get("playwright"):
                yield response.request.replace(
                    meta={**response.meta, "playwright": True},
                    dont_filter=True,
                )
            return

        yield {"url": response.url, "title": content.title, "markdown": content.markdown}

        for next_url in self._extract_links(response):
            yield scrapy.Request(next_url, callback=self.parse)

    def _extract_links(self, response: Any) -> set[str]:
        domain = self.allowed_domains[0]
        candidates: set[str] = set(response.css("a::attr(href)").getall())
        candidates.update(_QUOTED_URL_RE.findall(response.text))
        links: set[str] = set()
        for href in candidates:
            next_url = response.urljoin(href.strip())
            if is_crawlable_url(next_url, domain) and self._in_scope(next_url):
                links.add(next_url)
        return links

    def _in_scope(self, url: str) -> bool:
        return self.only_language is None or derive_language(url).value == self.only_language

    def _parse_sitemap(self, response: Any) -> Iterator[Any]:
        domain = self.allowed_domains[0]
        for loc in response.xpath("//*[local-name()='loc']/text()").getall():
            url = loc.strip()
            if not url:
                continue
            # Nested sitemaps (.xml) and in-scope crawlable pages dispatch through parse.
            is_page = is_crawlable_url(url, domain) and self._in_scope(url)
            if url.lower().endswith(".xml") or is_page:
                yield scrapy.Request(url, callback=self.parse)

    def _is_sitemap(self, response: Any) -> bool:
        if response.url.rstrip("/").lower().endswith(".xml"):
            return True
        content_type = response.headers.get("Content-Type", b"")
        return b"xml" in content_type.lower()

    def _playwright_enabled(self) -> bool:
        return bool(self.settings.getbool("SCRAPE_PLAYWRIGHT_ENABLED", False))
