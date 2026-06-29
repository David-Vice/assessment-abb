---
phase: P3
title: Indexing & RAG Core — libs/rag
depends_on: [P1]
enables: [P4, P8]
---

# P3 — Indexing & RAG Core (`libs/rag`)

The shared retrieval brain imported by every service: chunking, embeddings,
pgvector storage, hybrid retrieval, and BGE reranking. No HTTP here — pure,
testable library code. Satisfies brief requirement 2b (vector DB format) and the
retrieval half of 2c.

## Context from P2 (the corpus this consumes)

`corpus.json` is now clean and well-characterized, which shapes the decisions below:

- **~800 docs** (az 339 / en 212 / ru 251) — small; embedding + indexing cost is trivial (a few cents, seconds).
- **Language is content-verified** (P2 reconciles the URL prefix against detected content language), so language filtering is trustworthy. **EN is the smallest subset → cross-language fallback matters most there.**
- **`segment` is display/analytics metadata (citation badges, analytics mix), never a retrieval filter.**
- **Median ~400 tokens/doc** (p90 ~1k) → most documents are a **single chunk**; only long pages split.
- **~31% carry markdown headings** (P2 promotes `<h1>`–`<h6>`) → heading-aware splitting is viable, with a size-based fallback for the rest.
- **`content_hash` is whitespace-normalized** → idempotent re-ingest is reliable.
- **Residual cross-page boilerplate** (e.g. the "open a business account" / app-download promo block on ~40 pages) is intentionally left for **chunk-level dedup here** (the P2 deferral).

## Decisions

1. **Heading-aware chunking with a size-based fallback, ~512–1024 tokens, small overlap**
   - Decision: Split markdown on heading structure where present (~31% of docs), else a recursive token splitter; pack into 512–1024-token chunks (~80-token overlap), preserving heading breadcrumbs in the chunk text where available. Token counts via `tiktoken` (`cl100k_base`, the `text-embedding-3-large` encoding).
   - Rationale: respects structure where the page has it; the corpus is single-chunk-dominant (median ~400 tokens), so most docs stay whole and only long pages split.
   - Alternatives: fixed-size only (loses structure — rejected); proposition-level (overkill for v1 — deferred).

2. **`text-embedding-3-large` (3072-dim → `halfvec`), batched + retry**
   - Decision: Embed chunks in batches through LangChain `OpenAIEmbeddings`; store 3072 dims as **`halfvec(3072)`** (pgvector caps `vector` HNSW at 2000 dims — `halfvec` indexes to 4000 at half storage, negligible recall loss). Retry/backoff on every call; assert returned dimension.
   - Rationale: Decision 7; multilingual quality for AZ/RU. Tiny corpus (~1.2–1.8k chunks) → cost and latency are negligible.

3. **Hybrid retrieval = dense + sparse, fused with RRF**
   - Decision: Run pgvector cosine ANN (HNSW over `halfvec_cosine_ops`) and language-uniform full-text in parallel, fuse with Reciprocal Rank Fusion, return top ~30–50 candidates.
   - Rationale: Dense handles paraphrase, sparse handles exact product names/terms; RRF is robust and parameter-light. One SQL round per branch, no extra engine.

4. **BGE cross-encoder rerank → top-k**
   - Decision: `BAAI/bge-reranker-v2-m3` via LangChain `ContextualCompressionRetriever` re-scores candidates; keep top 5–8 for generation. Lazy-loaded, CPU, env toggle `RERANK_ENABLED`.
   - Rationale: Decision 5; highest-ROI precision gain; self-hosted.
   - Runs **off the event loop** (`asyncio.to_thread`) so the CPU-bound cross-encoder never blocks concurrent chat requests.
   - Cost note: this is the heaviest dependency (pulls `torch`) — it dominates image size and adds a one-time cold-start load. Lazy-load keeps startup cheap and `RERANK_ENABLED=false` skips loading the model entirely (hybrid search still answers); note the `torch`/`sentence-transformers` packages are still *installed* unless the image is built without the reranker dependency.

5. **Equal AZ / RU / EN support (first-class, no second-class language)**
   - Decision: All three languages are treated identically. (a) **Dense:** the multilingual `text-embedding-3-large` carries semantic recall equally across AZ/RU/EN — no per-language model. (b) **Sparse:** the `tsv` column is built uniformly via `to_tsvector('simple', immutable_unaccent(content))` + `pg_trgm` on `content` — no Postgres language stemmer is used for any language, so none is privileged (this also resolves the fact that Postgres has no Azerbaijani FT config). (c) **Filter/boost** by request language with cross-language fallback when hits are sparse — language tags are content-verified upstream (P2), and EN is the smallest subset so fallback matters most there.
   - Rationale: ABB's primary language is Azerbaijani; using English/Russian stemmers but a degraded path for AZ would make AZ second-class. Uniform `simple`+`unaccent`+trigram + multilingual embeddings gives genuinely equal treatment.
   - Trade-off accepted: no language-specific stemming for EN/RU either (slightly less sparse recall on those) — acceptable because dense retrieval + reranking dominate quality, and equality across languages is the explicit requirement.

6. **Idempotent indexing keyed by `content_hash`**
   - Decision: Re-ingesting an unchanged document is a no-op (its whitespace-normalized `content_hash` already matches); a changed `content_hash` replaces that document's chunks transactionally.
   - Rationale: Safe re-runs, incremental updates, no duplicate vectors. Re-uploading the same `corpus.json` does nothing.

7. **Chunk-level dedup (fulfills the P2 deferral)**
   - Decision: During ingestion, normalize each chunk and (a) drop exact duplicates within a document, and (b) drop **short cross-page boilerplate chunks** — content recurring across many documents (document-frequency ≥ threshold) **and** under a length guard, e.g. the repeated "open a business account" / app-download promo block. The length guard ensures a long *substantive* shared chunk (a real disclosure, fee table) is never dropped.
   - Rationale: avoids wasted embeddings, duplicate citations, and a generic banner out-ranking real content. This is where P2's deferred near-duplicate / promo-snippet handling lands.
   - Scope: the document-frequency scan runs over the whole corpus at ingest. An incremental re-ingest of a subset does **not** retroactively prune boilerplate from already-indexed unchanged documents (acceptable for the one-shot demo ingest; a full re-ingest reconciles).

## Plan

### Module map (`libs/rag/`)
- `chunking.py` — `chunk_document(doc: CorpusDocument) -> list[Chunk]` (heading-aware + recursive fallback, token-budgeted; single chunk for short docs).
- `embeddings.py` — `embed_texts(texts) -> list[Vector]` (batched, retry/backoff, dimension assertion).
- `vectorstore.py` — upsert documents/chunks; transactional replace-on-hash-change.
- `retriever.py` — `hybrid_search(query, language, k) -> list[Candidate]` (dense + sparse + RRF).
- `rerank.py` — `rerank(query, candidates, top_k) -> list[Candidate]` (BGE, lazy, toggleable).
- `pipeline.py` — `ingest_corpus(corpus)` and `retrieve(query, language)` orchestration used by services.
- `db.py` — async SQLAlchemy/psycopg pool + query helpers. Schema is owned by `infra/postgres/init.sql` (P1); this layer only connects and queries.

### Retrieval flow
```
query, language
  → embed query (multilingual; equal for az/ru/en)
  → dense: HNSW cosine top-N over halfvec (filter language, fallback any)
  → sparse: to_tsquery('simple', immutable_unaccent(q)) on tsv + pg_trgm similarity on content, top-N
  → RRF fuse → candidates[~40]
  → BGE rerank → top_k[~6]
  → return chunks + source metadata (url, title, language, segment)
    (segment is carried for citations/analytics — never a retrieval filter)
```

### RRF (reference)
```python
def rrf(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores
```

## Breakdown

- **`chunking.py`**: markdown heading parser + recursive token packer (`tiktoken`/`cl100k_base`); heading breadcrumbs where present; single-chunk for short docs; unit tests on fixture docs (boundary/overlap, heading vs no-heading).
- **`embeddings.py`**: batched OpenAI embeddings with concurrency limit + retry; assert 3072 dims.
- **`vectorstore.py`**: `upsert_document`, `replace_chunks`, store `embedding` as `halfvec(3072)`; **`tsv` is a DB-GENERATED column — insert `content` only, never write `tsv`**; apply chunk dedup (Decision 7) before embedding; hash-change detection (transactional replace).
- **`retriever.py`**: dense (`halfvec_cosine_ops`) + sparse (`simple`+`unaccent` `tsquery` on `tsv`, `pg_trgm` on `content`) queries, RRF fusion, language filter + cross-language fallback; segment returned, not filtered.
- **`rerank.py`**: lazy BGE load (`sentence-transformers`/`FlagEmbedding`), batch score, `RERANK_ENABLED` toggle.
- **`pipeline.py`**: `ingest_corpus` (chunk → dedup → embed → upsert) used by the worker; `retrieve` (hybrid → rerank) used by chat.
- **Tests**: RRF unit test; chunking + chunk-dedup unit tests; retrieval integration test against a seeded test DB (docker pg CI service) with a tiny fixture corpus; rerank ordering test.
- **Docs**: `libs/rag/README.md` — retrieval architecture diagram + tuning knobs (chunk size, N, k, RRF k, dedup DF threshold).
- **Verification**: ingest sample corpus → chunk counts match expectation; a known question retrieves its source page in top-k; cross-page promo chunks are dropped (no generic banner in results); re-ingesting the same corpus is a no-op (idempotent); rerank improves ordering vs no-rerank on a spot-check set.
