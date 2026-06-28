# ABB Scraper

A single command that crawls the ABB Bank website and produces `corpus.json` — the
artifact a user uploads into the web app and the ingestion service indexes.

## Run

```bash
uv run abb-scrape --out corpus.json
```

That's the whole "scraping script" the brief asks for: one command in → one
`corpus.json` out. Internally it uses Scrapy (crawl engine), trafilatura (clean
markdown extraction), and optionally Playwright (JS fallback).

### Flags

| Flag | Default | Purpose |
| ---- | ------- | ------- |
| `--out PATH` | `corpus.json` | Output file |
| `--start-url URL` | `https://abb-bank.az/` | Crawl entry point |
| `--max-pages N` | `300` | Stop after N pages (bounded runs) |
| `--max-depth N` | `5` | Max link depth |
| `--playwright` | off | Headless-browser fallback for JS-rendered pages |
| `--only-language az\|en\|ru` | off | Restrict the crawl to one language tree (for balanced corpora) |
| `--sample` | off | Also write a trimmed `corpus.sample.json` |
| `--sample-size N` | `25` | Documents in the sample |
| `--merge A B C` | off | Merge corpus files into `--out` (dedup by content hash) and exit |

Defaults also come from `.env` (`SCRAPE_*`), overridden by flags.

### Examples

```bash
# Quick bounded crawl for local testing
uv run abb-scrape --out corpus.json --max-pages 40

# Enable JS rendering (requires: uv run playwright install chromium)
uv run abb-scrape --out corpus.json --playwright
```

### Balanced multilingual corpus (recommended)

ABB is a Next.js i18n site whose sitemap is overwhelmingly Azerbaijani, and the
language trees interlink unevenly — so a single crawl skews heavily by language.
To build a balanced AZ/RU/EN corpus, crawl each language tree separately (DFS,
in-language link-following) and merge:

```bash
uv run abb-scrape --only-language ru --out corpus.ru.json --max-pages 450
uv run abb-scrape --only-language en --out corpus.en.json --max-pages 450
uv run abb-scrape --only-language az --out corpus.az.json --max-pages 700
uv run abb-scrape --merge corpus.az.json corpus.en.json corpus.ru.json --out corpus.json --sample
```

Each scoped pass stays within its language (`--only-language` filters every link
and skips the language-mixing sitemap). `--merge` de-duplicates by content hash
and `--sample` writes a balanced `corpus.sample.json`. The committed sample was
built this way (~balanced across AZ/RU/EN and the individuals/business/about
sections).

## Output schema

```json
{
  "version": 1,
  "source": "abb-bank.az",
  "generated_at": "2026-06-28T00:00:00Z",
  "documents": [
    {
      "url": "https://abb-bank.az/en/ferdi/...",
      "language": "en",
      "segment": "individuals",
      "title": "Wire transfers",
      "markdown": "# Wire transfers\n\n...",
      "content_hash": "sha256:...",
      "fetched_at": "2026-06-28T00:00:00Z"
    }
  ]
}
```

Validated against `abb_contracts.Corpus` / `CorpusDocument`.

## Behavior

- **Polite by default:** obeys `robots.txt`, AutoThrottle on, conservative concurrency, identifies via a custom User-Agent.
- **Coverage:** seeds from `sitemap.xml` and the AZ/EN/RU language roots, then follows in-domain links (BFS, depth-limited).
- **Clean text:** trafilatura strips nav/ads/footers → markdown; pages with too little content are dropped.
- **Deduplicated:** identical content (by SHA-256) is dropped; output sorted by URL for stable diffs.
- **Metadata:** `language` and `segment` are derived from the URL for downstream filtered retrieval.

## Playwright (optional)

Off by default — ABB is mostly server-rendered, so plain HTTP covers the site.
When `--playwright` (or `SCRAPE_PLAYWRIGHT_ENABLED=true`) is set, a page that
extracts to too little text is re-fetched with a headless browser. Requires a
one-time browser install: `uv run playwright install chromium`.

## Tests

Pure logic (URL→language/segment, extraction, hashing, sampling, export) is unit
tested offline — no network:

```bash
uv run pytest apps/scraper
```

## Known limitations / future enhancements

- **Exact-hash dedup only.** Pages are deduped by SHA-256 of extracted markdown.
  Near-duplicates (same disclosure across pages, minor timestamp diffs) are not
  collapsed. A SimHash/Hamming-distance pass, or paragraph-level dedup at the
  chunking step (P3), would handle these — deferred to keep the crawler simple.
- **Synchronous extraction.** trafilatura runs in the crawl callback. Fine for a
  single bounded site; for very large crawls, offload to a thread/process pool or
  extract offline from stored HTML.

