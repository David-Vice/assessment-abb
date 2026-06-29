# P2 Scraper — Multi-Perspective Code Review

> Cross-validated review of the P2 scraper (`apps/scraper/`) at commit `a5737b9`
> ("Fixed crawler and data quality"). Diff base: `25ac0b3` (pre-P2). Four isolated
> reviewers on different models, followed by an orchestrator audit that validated
> every load-bearing finding against the code and the freshly-crawled corpus.

## Methodology

- **Reviewers (parallel, isolated, different models):** [Alpha](c974ba1a-7939-427f-b403-6b91918ff0f1) (opus-max), [Beta](f368a844-d758-42cc-8d80-076d8531e895) (gpt-5.4), [Gamma](d5012bc3-c441-488c-bccd-fdffb0bc1b17) (composer-2), [Delta](de120fe8-c7d5-4119-8bff-5d22528b7733) (sonnet).
- **Audit:** findings cross-checked, validated by running the actual code (`extract_rendered`, `asyncio.Semaphore`), measuring the new `corpus.json`/`corpus.sample.json`, and externally validating the Playwright cleanup contract.
- **Gates at HEAD:** `ruff check` ✅ · `mypy --strict` ✅ · `pytest` ✅ (34) · corpus 779 docs, 0 dup/0 hash-mismatch/schema-valid. **`ruff format --check` ❌** on committed `a5737b9` (2 files — see L12; corrected in working tree).

## Verdict

**Solid, ship-capable core with high-confidence robustness gaps to close.** The architecture (clean module split, pure helpers, frozen value objects, deterministic merge/sample, robots obedience, host-scoping) is genuinely good and well-tested where tests exist. The real risk is concentrated in the **error paths of the async crawl engine** (`render.py`) and **two of my prior "fixed" claims that the reviewers correctly partially refuted** (inline fusion, language accuracy). No Critical defects; **3 High, 7 Medium, 12 Low**.

## Remediation status (addressed after review)

All High findings and most Medium/Low were fixed in a follow-up pass — gates green (`ruff check` · `ruff format --check` · `mypy --strict` · `pytest` **46**) and a clean re-crawl applied the data fixes.

| Finding | Status |
| --- | --- |
| H1 crawl-abort + browser leak | ✅ Fixed — extraction moved inside the per-page guard, `gather(return_exceptions=True)`, browser `try/finally`, and `_visible_text` swallows `ParserError` |
| H2 silent empty corpus | ✅ Fixed — sitemap `.ok` check + raise on empty frontier / 0 documents (`ExternalServiceError`) |
| H3 no engine/CLI tests | ✅ Fixed — `test_render.py` (sitemap parse / select / dedupe-containment), `test_cli.py` (bounds) |
| M1 `Any` types | ✅ Fixed — `BrowserContext` / `FilteringBoundLogger` annotations |
| M2 inline fusion | ◑ Mitigated — inline+block separation in `_visible_text`; residual no-whitespace source-DOM cases documented |
| M3 language by URL | ✅ Fixed — content reconciliation (py3langid, az/en/ru); 9 labels corrected on re-crawl |
| M4 robots fail-open | ✅ Fixed — fails closed on 5xx, honors `Crawl-delay` |
| M5 README drift | ✅ Fixed |
| M6 promo pages outside `/kampaniyalar/` | ◑ Documented (accepted scope) |
| M7 `--concurrency 0` hang | ✅ Fixed — `_positive_int` (`≥1`) on `--concurrency`/`--limit`/`--sample-size` |
| L1 www host · L2 source · L4 title unescape · L9 contract validators · L12 format | ✅ Fixed |
| L3 sitemap regex · L5 titles · L6 prose threshold · L7 intra-doc dup · L8 lxml mutation · L10 timestamps · L11 is_noise | Deferred / accepted (L6 superseded by ratio-based prose/visible selection) |

## Cross-model consensus matrix (top findings)

| Finding | Alpha | Beta | Gamma | Delta | Audit verdict |
| --- | :-: | :-: | :-: | :-: | --- |
| Crawl aborts on one degenerate page (+ browser leak) | ◑ | ✅ | ✅ | ✅ | **Confirmed — HIGH** (code+web validated) |
| Silent empty corpus on sitemap fetch failure | ✅ | ✅ | ✅ | ✅ | **Confirmed — HIGH** |
| No tests for `render.py` / `cli.py` | ✅ | ✅ | ✅ | ✅ | **Confirmed — HIGH** |
| `Any` on context/logger vs "No `Any`" rule | ✅ | ✅ | ✅ | ✅ | Confirmed — **MEDIUM** (Delta's "critical mypy gate" is wrong: `--strict` passes) |
| Inline label↔value fusion persists (~80 docs) | – | – | ✅ | – | **Confirmed — MEDIUM** (corrects prior "0 mashed") |
| Language-by-URL mismatch in sample | – | ◑ | ✅ | – | **Confirmed — MEDIUM** (1.3% corpus / 12% sample) |
| robots fail-open + ignores Crawl-delay | – | ✅ | ✅ | – | Confirmed — MEDIUM |
| `--concurrency 0` deadlocks | – | ✅ | ✅ | – | Confirmed — MEDIUM (validated) |

✅ flagged · ◑ partial/related · – not raised

---

## HIGH

### H1 — One degenerate page aborts the entire crawl and leaks the browser
`apps/scraper/abb_scraper/render.py` (`_render_one` ~L67-90, `render_corpus` gather ~L117-122)

`_render_one` only guards `goto`/`wait`/`content`. `extract_rendered(html)` runs **outside** the `try/finally`, and `asyncio.gather(...)` is called **without** `return_exceptions=True`. **Validated:** `extract_rendered("")`, `"   "`, and `"<!DOCTYPE html>"` all raise `lxml ParserError: Document is empty` (via `_visible_text` → `lxml_html.fromstring`). So a single blank/odd rendered page (plausible across ~900 URLs) propagates out of the worker → `gather` re-raises → `render_corpus` aborts **before** `write_corpus`, discarding the whole multi-minute crawl. **Externally validated:** `async with async_playwright()` only stops the driver connection (`_connection.stop_async()`), it does **not** close launched browsers — so the skipped `await browser.close()` (also `context.new_page()` is outside the guard) leaks a Chromium process on this path.
**Fix:** move extraction + `CorpusDocument` construction (and `new_page()`) inside the per-page guard; use `asyncio.gather(..., return_exceptions=True)` and skip/log failures; wrap the browser in `async with browser:` or `try/finally`.

### H2 — Silent empty corpus on sitemap failure (violates "fail loud", CONVENTIONS §1.4)
`render.py` (~L107-109, L131)

The sitemap fetch is not status-checked (unlike `_allowed_by_robots`, which checks `response.ok`). A 4xx/5xx/soft-404 or markup change yields `urls == []`; `gather` returns `[]`; `write_corpus(out_path, [], domain)` writes a **schema-valid empty** corpus and exits 0. Downstream ingestion would accept it and the RAG would answer "I don't know" to everything, with no signal that the scrape failed.
**Fix:** assert `sitemap.ok`; raise a typed error when 0 URLs are selected or 0 documents produced.

### H3 — No tests for `render.py` or `cli.py` (the most complex code)
`apps/scraper/tests/`

Excellent coverage for `extraction`/`metadata`/`exporters`/`sample`, but **zero** for the crawl engine and CLI. `parse_sitemap_locs`, `select_urls`, and `_allowed_by_robots` are pure/quasi-pure and trivially testable offline (mock the Playwright `context`/`request`). This is precisely why H1, H2, and the `--concurrency 0` hang all passed CI green.
**Fix:** offline tests with fakes for: sitemap non-200, empty URL set, robots filtering, extraction-exception containment, CLI arg validation, and `parse_sitemap_locs`/`select_urls` purity.

---

## MEDIUM

### M1 — `Any` on Playwright/logger params violates "No `Any`" (CONVENTIONS §1.7)
`render.py` (`context: Any`, `logger: Any` — L30, L67, L100), `cli.py` (L46, L55). Concrete types exist: `BrowserContext`/`Page`/`APIResponse` from `playwright.async_api`, and `get_logger` already returns `FilteringBoundLogger`. **Correction to Delta:** this is **not** a `mypy --strict` failure (explicit `Any` is allowed; the suite passes) — it's a hard *convention* violation. Fix by annotating concretely.

### M2 — Inline label↔value fusion persists (~80 docs) — corrects the prior "run-on fixed" claim
`extraction.py` `_visible_text` (block-tag separation only). The D4 fix newline-separates **block** elements but not adjacent **inline** `<span>`s, so calculator/spec widgets still fuse: **validated 80/779 docs** with letter→digit fusion (e.g. `ödənişi888.49`, `ay59`, `Push30`). The egregious block-level run-on (3382-char lines) is gone; this smaller inline class remains.
**Fix:** also insert a separator at inline boundaries (or a digit/letter boundary post-pass); add a regression test asserting label/value separation.

### M3 — Language derived from URL, not content (demo artifact over-exposed)
`metadata.py` `derive_language`. **Validated:** full corpus **10/779 = 1.3%** content/URL mismatch, but the committed **`corpus.sample.json` is 3/25 = 12%** (e.g. `/en/500-azn-kredit` is Azerbaijani; `/abb-biz-privacy` is English tagged `az`). The plan/README say "<1%" — accurate-ish for the corpus, **misleading for the sample a reviewer actually opens**. Either add offline content-language detection (reconcile vs URL) or correct the claim and accept it as a documented limit.

### M4 — robots.txt is fail-open and ignores `Crawl-delay`/`Request-rate`
`render.py` `_allowed_by_robots` (~L29-47). On any non-OK/exception it returns the full URL list (crawl-everything exactly when policy can't be evaluated), and only `can_fetch` is honored. For a bank target, prefer fail-closed (or explicit opt-out) and honor crawl-delay.

### M5 — Scraper README "Known limitations" is stale (doc drift)
`apps/scraper/README.md` L105-115 still says "Exact-hash dedup only / whitespace variants not collapsed" and "segment … fall to `other`" — both contradicted by shipped code (D7 whitespace-normalized hashing in `extraction.compute_content_hash`; D5 keyword classifier in `metadata.derive_segment`). The *plan* was updated; the README was not.
**Fix:** sync the README limitations to match (normalized dedup, segment classifier, segment = analytics metadata not a retrieval filter).

### M6 — Promo/expiry content survives outside `/kampaniyalar/`
`metadata.py` `NOISE_PATTERNS`. Excluding the `kampaniyalar` token doesn't catch promo pages at root SEO slugs: **validated 8 docs** with explicit expiry wording (`/6000-xosgeldin-mili`, `/ikiqat-xosgeldin-milleri`, `/en/sea-breezede-...-ipoteka-...`, "son tarix: 26.02.2026"). The campaign *section* is excluded, but campaign-style content at other URLs is not. Document the scope honestly, or add an expiry/promo content-signal.

### M7 — `--concurrency 0` deadlocks; no CLI bound validation
`cli.py` (bare `type=int`) → `render.py` `asyncio.Semaphore(concurrency)`. **Validated:** `Semaphore(0).acquire()` never returns. Negative `--limit`/`--sample-size` are also silently surprising. Add bounded parsers (`concurrency ≥ 1`, `limit ≥ 1`, `sample_size ≥ 1`).

---

## LOW

- **L1** `SCRAPE_START_URL=https://www.abb-bank.az/` breaks the host allowlist (`domain="www.abb-bank.az"` → apex URLs rejected → empty corpus). Canonicalize the host. *(Beta)*
- **L2** `source` inconsistency: `render_corpus` writes `domain`; `merge`/`sample` use the constant `"abb-bank.az"`. Diverges if `SCRAPE_START_URL` is overridden. *(Gamma, Delta)*
- **L3** `parse_sitemap_locs` regex is brittle (no CDATA/entity handling, no sitemap-index recursion; `.xml` filter tests the un-stripped `loc`). Works for ABB today; prefer `xml.etree`. *(Delta, Gamma)*
- **L4** Title regex doesn't HTML-unescape (`&amp;`/`&#39;` leak into titles), unlike the lxml body path. *(Gamma)*
- **L5** Some EN/RU pages get the generic pre-hydration title "ABB" (fixed 3 s settle vs Next.js title hydration). *(Gamma)*
- **L6** `MIN_PROSE_CHARS=400` > `MIN_CONTENT_CHARS=200`: clean prose of 200-399 chars is dropped in favor of noisier visible-text. *(Gamma)*
- **L7** Intra-document duplication (carousels/lists rendered twice) isn't collapsed (`content_hash` dedups across docs only). Deferred to P3 chunking. *(Gamma)*
- **L8** `_visible_text` mutates the lxml tree in place — safe (local tree) but a stylistic immutability nit. *(Delta; downgraded from its "High")*
- **L9** `packages/contracts` lacks format validators for `content_hash` (`^sha256:`) and `markdown` (min length). P1 scope. *(Delta)*
- **L10** Per-run `generated_at`/`fetched_at` churn the committed `corpus.sample.json` diff every regeneration. *(Gamma)*
- **L11** `is_noise` substring match could in principle false-positive (low risk given distinctive tokens). *(Delta)*
- **L12** Committed `a5737b9` **fails `ruff format --check`** (CONVENTIONS §12 gate) on `extraction.py` + `metadata.py` (magic-trailing-comma collections). Verification used `ruff check` only, not `ruff format --check`. **Validated** via `git stash` ("2 files would be reformatted"); corrected in the working tree. *(Audit — surfaced when a reviewer ran `ruff format`)*

---

## False positives & corrections

- **Delta C3 — "`Any` is a critical mypy `--strict` gate failure":** incorrect. `mypy --strict` **passes** (validated); explicit `Any` is allowed. Real issue, but a **convention** violation (Medium), not a CI/gate failure. Gamma had this calibrated correctly.
- **Delta C1/C2 elevated to "Critical":** recharacterized — silent-empty-corpus is **High** (failure handling, not data loss in normal runs); the browser-leak is folded into **H1** (real leak, externally validated).
- **"<1% language mismatch" (plan/README):** ~accurate for the full corpus (1.3%) but **wrong for the sample (12%)** — see M3.
- **My prior "D4: 0 mashed text" claim:** over-stated. Block-level run-on is fixed; **inline fusion remains (M2)**.

## Gaps the panel under-weighted

- The **committed demo artifact concentrates the defects**: diversified `(language × segment)` sampling over-selects the SEO product pages where language-mismatch (M3), inline fusion (M2), and promo content (M6) cluster — so `corpus.sample.json` looks materially worse than the 779-doc corpus. This is the file a reviewer opens first.

## Conventions compliance (`CONVENTIONS.md`)

| Area | Status | Note |
| --- | :-: | --- |
| Immutability (§1.2) | ✅ | frozen `ExtractedContent`; pure helpers; lxml mutation is local (L8) |
| Fail loud (§1.4) | ⚠️ | H2 (silent empty corpus), M4 (robots fail-open) |
| No `Any` (§1.7) | ❌ | M1 |
| One module = one domain (§1.6) | ✅ | clean split |
| Tests prove behavior (§1.11, §8) | ⚠️ | strong where present; H3 gap on engine/CLI |
| ruff/mypy strict green (§10, §12) | ⚠️ | `ruff check` + `mypy --strict` green; **`ruff format --check` failed on committed code** (L12), fixed in tree |
| Enum values = ISO/wire (§1.8) | ✅ | `az/en/ru`, segment tokens |

## Recommended remediation order

1. **H1 + H2** (small, surgical, high-impact resilience): guard extraction, `return_exceptions=True`, `async with browser`, check `sitemap.ok`, fail on 0 docs.
2. **H3**: offline tests for `render.py`/`cli.py` pure helpers + failure paths.
3. **M1, M5, M7**: concrete types, README sync, CLI bound validation (all quick).
4. **M2, M3, M6**: either fix (inline separator; content language detection) or honestly re-scope the docs.
5. **Low**: opportunistic.
