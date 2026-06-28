# Investigation Journal

Concise record of non-obvious findings discovered while building this project.
Newest sections first. Keep entries short — *why* and *what we decided*, not narration.

---

## ABB website (crawl target)

- **What it is:** ABB = Azerbaijan's largest bank (ex–International Bank of Azerbaijan). Official site: `https://abb-bank.az/`.
- **Tech:** **Next.js i18n** site (confirmed via response headers: `X-Nextjs-Cache`, `Set-Cookie: NEXT_LOCALE=…`, `rsc`/`next-router` headers). Server-rendered HTML, so plain HTTP crawling works (no JS engine needed for content).
- **Languages & URL scopes:**
  - **AZ** (default/primary) → root paths, e.g. `https://abb-bank.az/ferdi`
  - **EN** → `https://abb-bank.az/en/...`
  - **RU** → `https://abb-bank.az/ru/...`
  - Language is derived from the **first URL path segment** (`/en/`, `/ru/`, else AZ).
- **Site segments** (derived from path keywords):
  - `individuals` ← `ferdi` (or `individual`)
  - `business` ← `biznes` (or `business`)
  - `about` ← `haqqimizda` (or `about`)
  - everything else → `other` (e.g. `/xeberler` news)
- **Host scope:** only the apex + `www` are crawled. Other subdomains are **excluded** — notably `prime.abb-bank.az` (the login/banking portal: not public info content, and its `robots.txt` returns 500).

## Crawl/corpus findings (Phase P2)

- **The sitemap is misleading.** `sitemap.xml` (and robots-declared sitemaps) are **~99% Azerbaijani** and dominated by `/haqqimizda` news/about URLs. A naive sitemap-driven crawl yields ~1,400 docs but **AZ-only** (EN/RU ≈ 1 each).
- **Languages interlink unevenly.** The AZ homepage has **zero** links to EN/RU versions. RU/EN pages *do* link richly within their own language (~109 links each), but those links live in **Next.js JSON/script blobs, not `<a href>` tags** → anchor-only extraction misses entire languages. Fix: also harvest quoted URLs from the raw HTML via regex.
- **BFS starved the small languages.** Breadth-first (Scrapy `DEPTH_PRIORITY`) drowned EN/RU behind the AZ flood. **Depth-first** (Scrapy default) follows each language tree properly. → reverted to DFS.
- **Cookies pin language.** `NEXT_LOCALE` cookie can make the server serve one language for later requests; we crawl cookie-less (`COOKIES_ENABLED=False`) so each URL serves its own language.
- **Balanced corpus strategy (chosen):** crawl each language **separately** (`--only-language`, in-language DFS, sitemap skipped) then **merge + dedup by content hash**. Result: ~balanced AZ/RU/EN.
- **Why AZ is still largest:** AZ is the primary market language → a few more reachable pages. Small, expected gap (e.g. az:133 vs en:103 / ru:108).
- **Coverage caveat:** the balanced corpus covers the **main navigable content per language**, not ABB's full AZ news archive. Exhaustive (unscoped) crawling is possible but ~99% AZ.
- **Tooling note:** Scrapy 2.16 replaced `start_requests` with `async def start()`. Scrapy 2.16 ships type hints (no mypy stub override needed); `trafilatura` does not.

## Infra findings (Phase P1)

- **pgvector + 3072-dim embeddings:** pgvector's HNSW/IVFFlat index caps the `vector` type at **2000 dims**, but `text-embedding-3-large` is **3072**. Use **`halfvec(3072)`** (indexable to 4000 dims, half storage, negligible recall loss).
- **Postgres generated column needs IMMUTABLE:** `unaccent()` is `STABLE`, so a `GENERATED ALWAYS AS (... unaccent ...) STORED` column is rejected. Wrap it in a custom `IMMUTABLE` `immutable_unaccent()` function.
- **Equal AZ/RU/EN full-text:** Postgres has no Azerbaijani FT config, so the `tsv` column uses uniform `simple` + `unaccent` + `pg_trgm` for all languages (no language privileged); multilingual semantic recall comes from the dense embeddings.
- **CI must live in `.github/workflows/`** — GitHub doesn't discover workflows elsewhere.
