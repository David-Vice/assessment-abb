---
phase: P2
title: Scraper — abb-bank.az → corpus.json
depends_on: [P1]
enables: [P3, P4]
---

# P2 — Scraper

Crawl ABB Bank's official website and emit a clean, metadata-rich `corpus.json`
that is both the user-uploadable artifact (Decision: localStorage upload) and the
ingestion-service input. Satisfies brief requirement 1.

> **Brief mapping (explicit):** the brief asks for *"a script to parse the ABB
> website."* This is delivered as exactly that — **a single runnable command**,
> `abb-scrape --out corpus.json` (documented front-and-center in the README).
> Scrapy/Playwright/trafilatura are the internals of that one script, not extra
> moving parts the reviewer must operate. One command in → one `corpus.json` out.

## Decisions

1. **Scrapy as the crawl engine, Playwright only as fallback**
   - Decision: `scrapy` drives the crawl (frontier, dedup, retries, autothrottle, robots.txt). `scrapy-playwright` renders only pages flagged as JS-dependent.
   - Rationale: ABB content is mostly server-rendered (confirmed in research) — HTTP for the ~90%, headless browser for the rest. Maximizes speed and politeness; avoids running a browser for every page.
   - Alternatives: Firecrawl (hosted, per-page cost, external dep — rejected for reproducibility); httpx+BS4 (rebuilds crawl plumbing — rejected).

2. **trafilatura for content extraction**
   - Decision: Convert each page's HTML to clean markdown/text via `trafilatura` (fallback to readability if extraction yields too little).
   - Rationale: Best-in-class boilerplate removal (nav/ads/cookie banners) while preserving headings/lists — directly improves downstream chunk quality.

3. **Sitemap-seeded, language- and segment-aware crawl**
   - Decision: Seed from `https://abb-bank.az/robots.txt` → `sitemap.xml`; if absent, BFS from the three language roots (`/` AZ, `/en/`, `/ru/`). Derive `language` from URL prefix and `segment` from path (`ferdi`/individuals, `business`, `haqqimizda`/about).
   - Rationale: Sitemaps give canonical coverage; URL-derived metadata powers multilingual + filtered retrieval later.

4. **Deterministic, deduplicated output keyed by content hash**
   - Decision: Each record carries a SHA-256 `content_hash`; identical content across URLs is dropped. Output sorted by URL for stable diffs.
   - Rationale: Stable, reviewable artifact; enables incremental re-crawl and prevents duplicate chunks.

5. **Committed sample corpus for demo safety**
   - Decision: Commit a trimmed `corpus.sample.json` so the demo never depends on a live crawl.
   - Rationale: Risk mitigation — bank site could throttle/block during the demo.

## Plan

### Output schema (`CorpusDocument` from `packages/contracts`)
```json
{
  "url": "https://abb-bank.az/en/ferdi/...",
  "language": "en",
  "segment": "individuals",
  "title": "Wire transfers",
  "markdown": "# Wire transfers\n\n...",
  "content_hash": "sha256:...",
  "fetched_at": "2026-06-26T12:00:00Z"
}
```
The full corpus is `{ "version": 1, "source": "abb-bank.az", "generated_at": ..., "documents": [ ... ] }`.

### Crawl configuration
- `ROBOTSTXT_OBEY = True`, `AUTOTHROTTLE_ENABLED = True`, conservative `CONCURRENT_REQUESTS_PER_DOMAIN`, custom `USER_AGENT` identifying the bot.
- Allowed domain restricted to `abb-bank.az`; skip binary/asset URLs (pdf/img handled separately or skipped for v1 — text-only per brief).
- Playwright enabled per-request via `meta={"playwright": True}` only when a heuristic (empty `trafilatura` result on raw HTML) triggers a re-fetch.
- Page cap + depth cap from env (`CRAWL_MAX_PAGES`, `CRAWL_MAX_DEPTH`) for bounded runs.

### Pipeline
1. Spider yields raw HTML + URL metadata.
2. Item pipeline: `trafilatura` extract → markdown; compute `content_hash`; derive `language`/`segment`; drop empties + dupes.
3. Exporter writes a single `corpus.json` (and updates `corpus.sample.json` when `--sample`).

## Breakdown

- **`apps/scraper/`**: Scrapy project (`scrapy.cfg`, `settings.py`, `pyproject.toml` deps: scrapy, scrapy-playwright, trafilatura, contracts).
- **`spiders/abb.py`**: `SitemapSpider`/`CrawlSpider` hybrid — sitemap seed with BFS fallback; per-URL language/segment derivation; Playwright fallback heuristic.
- **`pipelines.py`**: extraction (trafilatura), hashing, dedup, validation against `CorpusDocument`.
- **`exporters.py`**: write `corpus.json` envelope; `--sample` mode.
- **`run.py` / CLI**: `uv run abb-scrape --out corpus.json [--max-pages N] [--sample]`.
- **Tests**: unit tests for language/segment derivation + extraction on saved HTML fixtures (offline, no network).
- **Docs**: `apps/scraper/README.md` — how to run, flags, output schema, politeness notes.
- **Verification**: run against a small `--max-pages` budget; confirm AZ/EN/RU + all segments represented; schema-valid; dedup working; sample corpus committed.
