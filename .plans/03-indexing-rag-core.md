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

## Decisions

1. **Hierarchical + semantic chunking, ~512–1024 tokens, small overlap**
   - Decision: Split markdown by heading structure first, then pack into 512–1024-token chunks with ~80-token overlap, preserving heading breadcrumbs in chunk text.
   - Rationale: Research best practice for website content; respects document structure; balances context richness vs embedding/rerank cost.
   - Alternatives: fixed-size only (loses structure — rejected); proposition-level (overkill for v1 — deferred).

2. **`text-embedding-3-large`, batched via `embedMany` equivalent**
   - Decision: Embed chunks in batches through LangChain `OpenAIEmbeddings`; 3072 dims to match the pgvector column.
   - Rationale: Decision 7; multilingual quality for AZ/RU.

3. **Hybrid retrieval = dense + sparse, fused with RRF**
   - Decision: Run pgvector cosine ANN (HNSW) and language-uniform full-text in parallel, fuse with Reciprocal Rank Fusion, return top ~30–50 candidates.
   - Rationale: Dense handles paraphrase, sparse handles exact product names/terms; RRF is robust and parameter-light. One SQL round per branch, no extra engine.

4. **BGE cross-encoder rerank → top-k**
   - Decision: `BAAI/bge-reranker-v2-m3` via LangChain `ContextualCompressionRetriever` re-scores candidates; keep top 5–8 for generation. Lazy-loaded, CPU, env toggle `RERANK_ENABLED`.
   - Rationale: Decision 5; highest-ROI precision gain; self-hosted.

5. **Equal AZ / RU / EN support (first-class, no second-class language)**
   - Decision: All three languages are treated identically. (a) **Dense:** the multilingual `text-embedding-3-large` carries semantic recall equally across AZ/RU/EN — no per-language model. (b) **Sparse:** built uniformly with `to_tsvector('simple', unaccent(content))` + `pg_trgm` fuzzy matching — no Postgres language stemmer is used for any language, so none is privileged (this also resolves the fact that Postgres has no Azerbaijani FT config). (c) **Filter/boost** by request language with cross-language fallback when hits are sparse.
   - Rationale: ABB's primary language is Azerbaijani; using English/Russian stemmers but a degraded path for AZ would make AZ second-class. Uniform `simple`+`unaccent`+trigram + multilingual embeddings gives genuinely equal treatment.
   - Trade-off accepted: no language-specific stemming for EN/RU either (slightly less sparse recall on those) — acceptable because dense retrieval + reranking dominate quality, and equality across languages is the explicit requirement.

6. **Idempotent indexing keyed by `content_hash`**
   - Decision: Re-ingesting an unchanged document is a no-op; changed `content_hash` replaces that document's chunks transactionally.
   - Rationale: Safe re-runs, incremental updates, no duplicate vectors.

## Plan

### Module map (`libs/rag/`)
- `chunking.py` — `chunk_document(doc: CorpusDocument) -> list[Chunk]` (heading-aware, token-budgeted).
- `embeddings.py` — `embed_texts(texts) -> list[Vector]` (batched, retry/backoff).
- `vectorstore.py` — upsert documents/chunks; compute `tsv`; transactional replace-on-hash-change.
- `retriever.py` — `hybrid_search(query, language, k) -> list[Candidate]` (dense + sparse + RRF).
- `rerank.py` — `rerank(query, candidates, top_k) -> list[Candidate]` (BGE, lazy, toggleable).
- `pipeline.py` — `ingest_corpus(corpus)` and `retrieve(query, language)` orchestration used by services.
- `db.py` — async SQLAlchemy/psycopg pool + query helpers.

### Retrieval flow
```
query, language
  → embed query (multilingual; equal for az/ru/en)
  → dense: HNSW cosine top-N (filter language, fallback any)
  → sparse: to_tsquery('simple', unaccent(q)) + pg_trgm similarity top-N
  → RRF fuse → candidates[~40]
  → BGE rerank → top_k[~6]
  → return chunks + source metadata (url, title, language, segment)
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

- **`chunking.py`**: markdown heading parser + token packer (tiktoken for counts); unit tests on fixture docs (boundary/overlap correctness).
- **`embeddings.py`**: batched OpenAI embeddings with concurrency limit + retry; dimension assertion.
- **`vectorstore.py`**: `upsert_document`, `replace_chunks`, `tsv` population via `to_tsvector('simple', unaccent(content))` (uniform across AZ/RU/EN), hash-change detection.
- **`retriever.py`**: dense + sparse (`simple`+`unaccent` tsquery and `pg_trgm`) queries, RRF fusion, language filter + cross-language fallback.
- **`rerank.py`**: lazy BGE load (`sentence-transformers`/`FlagEmbedding`), batch score, `RERANK_ENABLED` toggle.
- **`pipeline.py`**: `ingest_corpus` (used by worker), `retrieve` (used by chat).
- **Tests**: RRF unit test; retrieval integration test against a seeded test DB (docker pg in CI service container) with a tiny fixture corpus; rerank ordering test.
- **Docs**: `libs/rag/README.md` — retrieval architecture diagram + tuning knobs (chunk size, N, k, RRF k).
- **Verification**: ingest sample corpus → counts match; a known question retrieves its source page in top-k; rerank improves ordering vs no-rerank on a spot-check set.
