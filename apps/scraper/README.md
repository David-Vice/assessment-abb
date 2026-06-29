# ABB Scraper

A single command that crawls the ABB Bank website and produces `corpus.json` — the
artifact a user uploads into the web app and the ingestion service indexes.

## Run

```bash
# one-time browser install (the crawl renders JS-heavy pages)
uv run playwright install chromium

# the whole "scraping script" the brief asks for: one command in → one corpus.json out
uv run abb-scrape --out corpus.json
```

Internally it drives a headless **Chromium** (Playwright) over the site's
`sitemap.xml`, extracts clean markdown with **trafilatura** (with an lxml
visible-text fallback for structured tables), and writes a schema-validated
`corpus.json`.

> **Why a browser?** ABB is a Next.js app: many pages (e.g. `haqqimizda/rekvizitler`
> requisites, card spec tables) render their content **and** their listing links via
> JavaScript, which a plain HTTP crawl can't see. Rendering the sitemap captures the
> complete, language-balanced URL set with its JS content.

### Flags

| Flag | Default | Purpose |
| ---- | ------- | ------- |
| `--out PATH` | `corpus.json` | Output file |
| `--only-language az\|en\|ru` | off | Restrict the crawl to one language tree (for balanced corpora) |
| `--concurrency N` | `5` | Concurrent browser pages |
| `--limit N` | off | Crawl at most N pages (bounded test runs) |
| `--sample` | off | Also write a trimmed `corpus.sample.json` |
| `--sample-size N` | `25` | Documents in the sample |
| `--merge A B C` | off | Merge corpus files into `--out` (dedup by content hash) and exit |

`SCRAPE_START_URL` (in `.env`) overrides the crawl entry point.

### Examples

```bash
# Quick bounded crawl for local testing
uv run abb-scrape --out corpus.json --limit 40
```

### Balanced multilingual corpus (recommended)

ABB's `sitemap.xml` is balanced by language but ordered AZ-first, so a single
capped crawl skews AZ. Crawl each language tree separately and merge:

```bash
uv run abb-scrape --only-language az --out corpus.az.json --concurrency 5 &
uv run abb-scrape --only-language en --out corpus.en.json --concurrency 5 &
uv run abb-scrape --only-language ru --out corpus.ru.json --concurrency 5 &
wait
uv run abb-scrape --merge corpus.az.json corpus.en.json corpus.ru.json --out corpus.json --sample
```

`--merge` de-duplicates by content hash and `--sample` writes a balanced
`corpus.sample.json` (round-robin across language × segment). The committed sample
was built this way (balanced across AZ/RU/EN and the individuals/business/about
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

- **Polite by default:** obeys `robots.txt`, identifies via a custom User-Agent, bounded concurrency paces the crawl.
- **Coverage:** seeds from `sitemap.xml`; excludes assets, login portals, and noise (`xeberler` news, `satinalmalar` procurement, `kampaniyalar` time-sensitive/untranslated campaigns).
- **Clean text:** trafilatura strips nav/ads/footers → markdown; an lxml fallback recovers structured tables; pages with too little content are dropped.
- **Deduplicated:** identical content (by SHA-256) is dropped; output sorted by URL for stable diffs.
- **Metadata:** `language` and `segment` are derived from the URL for downstream filtered retrieval.

## Tests

Pure logic (URL→language/segment, extraction, hashing, sampling, export/merge) is
unit tested offline — no network:

```bash
uv run pytest apps/scraper
```

## Known limitations / future enhancements

- **Exact-hash dedup only.** Near-duplicates (same disclosure across URLs,
  whitespace variants) are not collapsed. Paragraph-level dedup at the chunking
  step (P3) would handle these — deferred to keep the crawler simple.
- **Segment heuristic.** Root-level SEO landing pages (e.g. `/100-manat-kredit`)
  lack `ferdi`/`biznes` keywords and fall to `other`; a keyword/topic classifier
  could refine segment tagging.
- **Language by URL, not content.** A few untranslated `/en/`,`/ru/` pages carry
  source-language text but are tagged by URL prefix; content-based language
  detection is the production fix.
