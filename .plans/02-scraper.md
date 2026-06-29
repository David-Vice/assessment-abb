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
> Playwright/trafilatura are the internals of that one script, not extra moving
> parts the reviewer must operate. One command in → one `corpus.json` out.

## Decisions

1. **Headless-browser (Playwright) crawl over the sitemap**
   - Decision: `abb-scrape` drives a headless Chromium (`playwright`) over the URLs declared in `sitemap.xml`, rendering each page before extraction.
   - Rationale: ABB is a **Next.js app that renders both content *and* listing links via JavaScript** (confirmed in research). A plain HTTP crawl misses detail tables (e.g. `haqqimizda/rekvizitler`: TIN, SWIFT) and whole listing sections, capping coverage at ~344 nav-only pages. Rendering the sitemap captures the complete, language-balanced URL set with its JS content.
   - Alternatives: Scrapy HTTP crawl (server-rendered assumption is false here → misses JS content/links — rejected, removed); Firecrawl (hosted, per-page cost, external dep — rejected for reproducibility).

2. **trafilatura for content extraction, lxml visible-text fallback**
   - Decision: Convert each rendered page's HTML to clean markdown via `trafilatura` (`favor_recall`); when it returns too little (it discards structured tables), fall back to lxml visible-text with site chrome stripped.
   - Rationale: Best-in-class boilerplate removal for prose, while the fallback preserves the key/value tables (bank requisites, card specs) trafilatura drops — directly improves downstream chunk quality.

3. **Language reconciliation + segment classification**
   - Decision: Derive `language` from the URL prefix, then **reconcile against the detected content language** (py3langid, restricted to az/en/ru, high-confidence on sufficient text) — correcting untranslated `/en/`,`/ru/` pages that serve Azerbaijani text (and English `/privacy` pages under the AZ root). Derive `segment` from the URL: authoritative sections first (`biznes`/`sahibkar`/`korporativ`→business, `ferdi`→individuals, `haqqimizda`→about), then a retail-product keyword classifier for root-level SEO pages (`kredit`/`kart`/`əmanət`/`hesab`/…→individuals), else other. Business tokens take precedence over the retail keyword.
   - Rationale: content-reconciled language keeps AZ/RU/EN genuinely equal — URL prefixes lie on untranslated pages, so trusting them alone pollutes the per-language subsets. The keyword classifier cuts the `other` bucket from ~60% to ~11%. Segment is display/analytics metadata, **not** a retrieval filter.

4. **Deterministic, deduplicated output keyed by content hash**
   - Decision: Each record carries a SHA-256 `content_hash` computed over **whitespace-normalized** text, so spacing-only variants collapse to one document. Identical content across URLs is dropped; output sorted by URL for stable diffs.
   - Rationale: Stable, reviewable artifact; enables incremental re-crawl and prevents duplicate chunks (including trivial whitespace twins).

5. **Balanced multilingual corpus via per-language passes + merge**
   - Decision: The sitemap is balanced by language but ordered AZ-first; crawl each language tree separately (`--only-language`) then `--merge` (dedup by hash) into one balanced corpus.
   - Rationale: A single capped crawl skews AZ. Per-language passes guarantee AZ/EN/RU coverage.

6. **Committed sample corpus for demo safety**
   - Decision: Commit a trimmed `corpus.sample.json` (round-robin across language × segment) so the demo never depends on a live crawl and shows all languages/segments.
   - Rationale: Risk mitigation — the bank site could throttle/block during the demo; the full `corpus.json` is gitignored (rebuildable artifact).

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
- Polite by default: obeys `robots.txt` (`urllib.robotparser`) — **fails closed** on a robots server error (5xx) and honors `Crawl-delay`; identifies via a custom `USER_AGENT`; bounded concurrency (`--concurrency`, default 5) paces the crawl.
- Source URLs come from `sitemap.xml`; non-page/asset URLs and noise are excluded: `xeberler` (news), `satinalmalar` (procurement), `kampaniyalar` (time-sensitive offers, often untranslated → stale + language-mislabeled).
- Allowed host restricted to the canonical apex + `www` (`abb-bank.az`); login portals (`prime.*`/`online.*`) are out of scope.
- **Fails loud:** a non-OK sitemap/robots fetch, an empty frontier, or a zero-document crawl raises (no silent empty corpus). Per-page render/extraction errors are contained (the page is skipped, the crawl continues).
- `--limit` caps the page count for bounded test runs (validated `≥1`); `--only-language` scopes a pass.
- Rendering uses `wait_until="domcontentloaded"` + a fixed settle wait (ABB has no `<main>`; `networkidle` never settles here).

### Pipeline
1. Fetch `sitemap.xml`; select crawlable, non-noise, in-scope URLs; drop robots-disallowed.
2. Render each URL in headless Chromium; extract via trafilatura → markdown (lxml fallback for tables).
3. Derive `language`/`segment`; compute `content_hash`; drop empties + dupes.
4. Exporter writes a single `corpus.json` envelope (sorted by URL); `--sample` writes `corpus.sample.json`; `--merge` fuses per-language corpora.

## Breakdown

- **`apps/scraper/`**: package (`pyproject.toml` deps: playwright, trafilatura, lxml, contracts, rag-core). No Scrapy.
- **`render.py`**: async Playwright engine — sitemap fetch, robots filter, per-page render + extract, dedup, write.
- **`extraction.py`**: `extract_rendered` (trafilatura + lxml visible-text fallback); `compute_content_hash`.
- **`metadata.py`**: URL → language/segment derivation; `is_crawlable_url`; `is_noise`.
- **`exporters.py`**: write `corpus.json` envelope; `load_corpus`; `merge_corpora` (dedup by hash).
- **`sample.py`**: `select_sample` (round-robin across language × segment).
- **`cli.py` / CLI**: `uv run abb-scrape --out corpus.json [--only-language az|en|ru] [--concurrency N] [--limit N] [--sample] [--merge A B C]`.
- **Tests**: unit tests for language/segment derivation, extraction (prose + table fallback), hashing, sampling, export/merge (offline, no network).
- **Docs**: `apps/scraper/README.md` — how to run, flags, output schema, politeness notes, known limitations.
- **Verification**: run against a small `--limit` budget; confirm AZ/EN/RU + segments represented; schema-valid; dedup working; sample corpus committed.

## Known limitations / future enhancements

- **Semantic near-duplicates.** Whitespace-variant duplicates are now collapsed (normalized hashing); *semantically* near-identical pages (same disclosure reworded) are not — deferred to paragraph-level dedup at chunking (P3).
- **Segment heuristic.** A URL keyword classifier handles root-level SEO landing pages (`/100-manat-kredit`→individuals), cutting `other` to ~11%; the residual `other` is pages with no section or product keyword. A content/topic model could refine further. Note: segment is display/analytics metadata (citation badges, the analytics segment-mix chart), **not** a retrieval filter, so a miss never affects answer quality.
- **Language detection edge cases.** Language is reconciled from page content (py3langid, restricted to az/en/ru) against the URL prefix, correcting untranslated `/en/`,`/ru/` pages. Very short or heavily code-mixed pages may still keep the URL language.
- **Inline value fusion.** Block-level run-on is fixed; a few calculator/spec widgets render label and value as adjacent inline spans with no whitespace in the source DOM, which can still fuse (e.g. `ödəniş888.49`). A safe universal fix is constrained by legitimate alphanumerics (postal/SWIFT codes).
