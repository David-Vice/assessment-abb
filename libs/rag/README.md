# `abb-rag-core` (`libs/rag`)

The shared **retrieval brain** imported by every service. Pure, testable library
code — no HTTP. It turns the scraped corpus into a queryable knowledge base
(chunk → embed → store) and answers queries with hybrid retrieval + reranking.

Satisfies brief requirement **2b** (vector-DB format) and the retrieval half of
**2c**. Answer _generation_ lives in the chat service (P4); this layer only finds
the evidence.

## Module map

| Module | Responsibility |
| --- | --- |
| `chunking.py` | Heading-aware markdown split + token-window fallback (`tiktoken`/`cl100k_base`). Short docs stay whole; long sections split with overlap. |
| `dedup.py` | Drop *short* cross-page boilerplate (document-frequency threshold + length guard) + intra-doc duplicates, then re-number ordinals. |
| `embeddings.py` | `text-embedding-3-large` via LangChain `OpenAIEmbeddings` — batched, retried, dimension-asserted. |
| `vectorstore.py` | Idempotent upsert keyed by `content_hash`; halfvec literal insert. **Never writes the generated `tsv` column.** |
| `retriever.py` | Dense (HNSW cosine over `halfvec`) + sparse (`simple`+`unaccent` full-text + `pg_trgm`), fused with RRF, language-filtered with cross-language fallback. |
| `rerank.py` | BGE `CrossEncoder`, lazy-loaded, `RERANK_ENABLED` toggle. |
| `pipeline.py` | `ingest_corpus()` and `retrieve()` — the two entrypoints services call. |
| `db.py` / `models.py` / `rrf.py` | Async SQLAlchemy engine + session scope; `Chunk`/`RetrievedChunk`; reciprocal rank fusion. |

Schema is owned by `infra/postgres/init.sql` — this layer only connects and queries.

## Ingestion flow (`ingest_corpus`)

```
corpus.json
  → chunk every document (heading-aware, token-budgeted)
  → find short cross-page boilerplate (doc-frequency ≥ threshold, length-guarded) and drop it
  → skip documents whose content_hash already matches (idempotent)
  → embed surviving chunks in batches (text-embedding-3-large → 3072-dim)
  → upsert: insert halfvec embeddings; tsv is DB-generated
```

Re-ingesting an unchanged `corpus.json` is a no-op. A changed `content_hash`
transactionally replaces that document's chunks.

## Retrieval flow (`retrieve`)

```
query, language
  → embed query (multilingual; equal for az/ru/en)
  → dense:  HNSW cosine top-N over halfvec   (filter language, fallback any)
  → sparse: websearch_to_tsquery('simple', unaccent) on tsv
            + pg_trgm word-similarity         (filter language, fallback any)
  → RRF fuse → candidates (~40)
  → BGE rerank → top-k (~6)            [skipped if RERANK_ENABLED=false]
  → RetrievedChunk[] (content + url, title, language, segment, score)
```

`segment` is carried for citations/analytics — it is **never** a retrieval filter.

## Equal AZ / RU / EN support

All three languages are first-class:

- **Dense:** one multilingual embedding model — no per-language model.
- **Sparse:** `to_tsvector('simple', immutable_unaccent(content))` + trigram — no
  Postgres stemmer is used for _any_ language, so none is privileged (and Postgres
  has no Azerbaijani config to privilege anyway).
- **Filter + fallback:** results are filtered to the request language, falling back
  to any language when hits are sparse (matters most for EN, the smallest subset).

## Tuning knobs

| Knob | Where | Default | Effect |
| --- | --- | --- | --- |
| `RETRIEVAL_CANDIDATES` | env | 40 | Candidates pulled per branch before rerank. |
| `RETRIEVAL_TOP_K` | env | 6 | Chunks returned to the generator. |
| `RERANK_ENABLED` | env | `true` | Toggle the cross-encoder (off = skip model load; hybrid-only). |
| `RERANK_MODEL` | env | `BAAI/bge-reranker-v2-m3` | Cross-encoder model. |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | env | `text-embedding-3-large` / 3072 | Embedding model + asserted dimension. |
| `MAX_CHUNK_TOKENS` / `TARGET_CHUNK_TOKENS` / `OVERLAP_TOKENS` | `chunking.py` | 1024 / 800 / 80 | Chunk size ceiling, split target, overlap. |
| `BOILERPLATE_MIN_DOCS` / `BOILERPLATE_MAX_CHARS` | `dedup.py` | 8 / 400 | Drop a *short* chunk recurring across ≥ N docs (long shared content is kept). |
| `RRF_K` | `rrf.py` | 60 | RRF damping constant. |
| fuzzy floor | `pg_trgm.word_similarity_threshold` (GUC) | 0.6 | Threshold for the `<%` trigram fuzzy-recall operator. |

## Testing

**Unit (offline — no DB, no key):**

```bash
uv run pytest libs/rag -q
```
Covers chunking boundaries/overlap, boilerplate dedup, RRF fusion, and rerank ordering.

**End-to-end (real Postgres + OpenAI):** see `scripts/verify_rag.py` —
ingests the sample corpus, proves idempotency, and runs AZ/RU/EN retrieval.

```bash
DATABASE_URL=postgresql+psycopg://abb:abb@localhost:5433/abb_rag \
RERANK_ENABLED=false uv run python scripts/verify_rag.py
```

## Design notes

- **`halfvec(3072)`, not `vector`.** pgvector caps `vector` HNSW/IVFFlat indexes at
  2000 dims; `text-embedding-3-large` is 3072. `halfvec` indexes up to 4000 dims at
  half the storage with negligible recall loss.
- **LangChain is used only for embeddings.** Retrieval is custom SQL because
  hybrid + RRF + `halfvec` + equal-language fallback aren't cleanly expressible
  through LangChain's vectorstore/retriever abstractions. LangChain's orchestration
  role is the chat generation chain (P4).
- **Reranking adds image weight.** `sentence-transformers` pulls `torch` (the
  largest dependency). `RERANK_ENABLED=false` skips loading the model at runtime,
  but the package is still installed — a truly lean image needs a build without the
  reranker dependency.
- **Reranking runs off the event loop** (`asyncio.to_thread`) so the CPU-bound
  cross-encoder doesn't block concurrent chat requests.
- **Boilerplate is finalized at full ingest.** The document-frequency scan runs
  over the whole corpus; an incremental re-ingest of a subset does not retroactively
  prune boilerplate from already-indexed (unchanged) documents.
