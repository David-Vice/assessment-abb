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

- **Polite by default:** obeys `robots.txt` (fails closed on a robots server error; honors `Crawl-delay`), identifies via a custom User-Agent, bounded concurrency paces the crawl.
- **Coverage:** seeds from `sitemap.xml`; excludes assets, login portals, and noise (`xeberler` news, `satinalmalar` procurement, `kampaniyalar` time-sensitive/untranslated campaigns).
- **Clean text:** trafilatura strips nav/ads/footers → markdown; the site-wide feedback widget is stripped; an lxml fallback (block + inline separation) recovers structured tables; pages with too little content are dropped.
- **Deduplicated:** identical content (SHA-256 over whitespace-normalized text) is dropped; output sorted by URL for stable diffs.
- **Metadata:** `language` is reconciled from page content (py3langid) against the URL prefix; `segment` is classified from URL section + product keywords.
- **Fails loud:** a failed sitemap/robots fetch or a zero-document crawl raises instead of writing an empty corpus.

## Tests

Pure logic (URL→language/segment, extraction, hashing, sampling, export/merge) is
unit tested offline — no network:

```bash
uv run pytest apps/scraper
```

## Known limitations / future enhancements

- **Semantic near-duplicates.** Whitespace-variant duplicates are collapsed (the
  content hash is over whitespace-normalized text); *semantically* near-identical
  pages (the same disclosure reworded) are not — deferred to paragraph-level
  dedup at chunking (P3).
- **Segment residual.** A URL keyword classifier handles root-level SEO pages
  (`/100-manat-kredit` → individuals), cutting `other` to ~11%; the residual is
  pages with no section or product keyword. Segment is display/analytics
  metadata, not a retrieval filter.
- **Language detection edge cases.** Language is reconciled from content
  (py3langid, restricted to az/en/ru) against the URL prefix, correcting
  untranslated `/en/`,`/ru/` pages. Very short or heavily code-mixed pages may
  still keep the URL language.
- **Inline value fusion.** Block-level run-on is fixed; a few calculator/spec
  widgets render label and value as adjacent inline spans with no whitespace in
  the source DOM, which can still fuse (e.g. `ödəniş888.49`). A safe universal
  fix is constrained by legitimate alphanumerics (postal/SWIFT codes).
