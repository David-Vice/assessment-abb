---
phase: P1
title: Foundations — Monorepo, Tooling, Contracts, Infra Skeleton
depends_on: []
enables: [P2, P3, P4, P5, P6, P7, P8]
---

# P1 — Foundations

Establish the monorepo, shared contracts, data layer, and tooling that every
later phase builds on. Nothing user-facing ships here; the deliverable is a
skeleton that compiles, lints, types, and boots `docker compose` with empty
services.

## Decisions

1. **Monorepo, polyglot, no heavyweight orchestrator**
   - Decision: Plain directory monorepo (`apps/`, `libs/`, `packages/`, `infra/`) managed with **uv** (Python workspaces) for all Python apps and **pnpm** for `apps/web`. No Nx/Turborepo.
   - Rationale: Two language ecosystems make a single JS-centric monorepo tool awkward. `uv` gives fast, reproducible Python envs with a shared lockfile; pnpm matches the frontend repo. Keeps Docker builds simple (one toolchain per image).
   - Alternatives: Turborepo (JS-only, poor Python story — rejected); Poetry (slower than uv — rejected).

2. **Shared contracts as the schema authority**
   - Decision: `packages/contracts/` holds Pydantic v2 models for every cross-service payload (`CorpusDocument`, `IngestionJob`, `ChatRequest`, `ChatResponse`, `Citation`, analytics DTOs). Each FastAPI app imports them; the frontend consumes them via generated Zod schemas (from the OpenAPI document — Decision 2b).
   - Rationale: One source of truth across services *and* across the Python/TS boundary. Eliminates drift.

3. **Postgres + pgvector provisioned via init SQL**
   - Decision: `infra/postgres/init.sql` enables the `vector`, `unaccent`, and `pg_trgm` extensions and creates the schema (`documents`, `chunks`, `chat_logs`) with HNSW + GIN indexes. Run on container first-boot.
   - Rationale: Declarative, reproducible, reviewable. Migrations (Alembic) added only if schema churn demands it.

4. **Config via environment, validated with Pydantic Settings**
   - Decision: Each app has a `Settings` class (`pydantic-settings`) reading `.env`. Model names, DB/Redis URLs, OpenAI key, crawl limits all env-driven.
   - Rationale: Decision 7 requires env-driven models; keeps secrets out of code; 12-factor.

5. **CI scaffold first**
   - Decision: GitHub Actions workflow stub running `ruff` + `mypy` + `pytest` (Python) and `eslint` + `tsc` (web) from day one, even against empty packages.
   - Rationale: Code Quality is a scored criterion; cheaper to keep green continuously than retrofit.

## Plan

### Toolchain
- Python **3.12**, `uv` workspace at repo root (`pyproject.toml` with members `apps/*`, `libs/*`, `packages/*`).
- Lint/format: **ruff**; types: **mypy** (strict); tests: **pytest** + **pytest-asyncio**.
- Web: pnpm + Vite + TS (scaffolded fully in P5; here only the package + lint config).
- Pre-commit hooks: ruff, mypy, end-of-file/whitespace.

### Data schema (`infra/postgres/init.sql`)
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;   -- accent-insensitive full-text for AZ/RU/EN
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- language-agnostic fuzzy keyword matching

CREATE TABLE documents (
  id            BIGGENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  url           TEXT NOT NULL UNIQUE,
  language      TEXT NOT NULL,            -- 'az' | 'en' | 'ru'
  segment       TEXT,                     -- 'individuals' | 'business' | 'about' | ...
  title         TEXT,
  content_hash  TEXT NOT NULL,
  fetched_at    TIMESTAMPTZ NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
  id            BIGGENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  document_id   BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal       INT NOT NULL,
  content       TEXT NOT NULL,
  language      TEXT NOT NULL,
  segment       TEXT,
  embedding     VECTOR(3072),             -- text-embedding-3-large
  tsv           TSVECTOR,
  token_count   INT
);
CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_tsv_gin        ON chunks USING gin (tsv);
CREATE INDEX chunks_lang_idx       ON chunks (language);

CREATE TABLE chat_logs (
  id            BIGGENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id    UUID NOT NULL,
  question      TEXT NOT NULL,
  answer        TEXT NOT NULL,
  language      TEXT,
  citations     JSONB NOT NULL DEFAULT '[]',
  retrieved_ids BIGINT[] NOT NULL DEFAULT '{}',
  model         TEXT,
  prompt_tokens INT, completion_tokens INT,
  latency_ms    INT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX chat_logs_session_idx ON chat_logs (session_id);
CREATE INDEX chat_logs_created_idx ON chat_logs (created_at);
```
> Notes:
> - `BIGGENERATED` above is shorthand — use `BIGINT GENERATED ALWAYS AS IDENTITY` in the real file. HNSW dim must match the chosen embedding model (3072 for `-3-large`).
> - **Equal AZ/RU/EN support (Decision: same-level multilingual):** Postgres ships full-text configs for `english`/`russian` but **not Azerbaijani**. To treat all three languages identically, `tsv` is built uniformly with `to_tsvector('simple', unaccent(content))` (no per-language stemming privileges any language) and complemented by `pg_trgm` fuzzy matching. Semantic recall is carried equally across languages by the multilingual `text-embedding-3-large` dense vectors.
> - **Migrations:** `init.sql` runs on first boot (demo scope). Alembic is documented as the production upgrade path (not added now).

### docker-compose skeleton
Services defined but minimal: `postgres` (with init.sql mounted), `redis`, and placeholder builds for `ingestion`, `chat`, `analytics`, `web` (each a healthcheck-only FastAPI/Vite stub). Full Dockerfiles land in P7; here they just boot.

## Breakdown

- **Root workspace**: `pyproject.toml` (uv workspace, ruff, mypy, pytest config), `.python-version`, `.gitignore`, `.env.example` (OPENAI_API_KEY, CHAT_MODEL=gpt-4o, AUX_MODEL=gpt-4o-mini, EMBEDDING_MODEL=text-embedding-3-large, DATABASE_URL, REDIS_URL, crawl limits).
- **Root `README.md` (from day 1, grows each phase)**: project vision, architecture diagram, one-command quickstart (`cp .env.example .env` → `docker compose up`), and a requirement→component map. Documentation is foregrounded, not deferred to P8 (P8 only finalizes it). Each later phase appends its service section.
- **`packages/contracts/`**: Pydantic v2 models — `CorpusDocument`, `Citation`, `ChatRequest`, `ChatResponse`, `IngestionJob`/`IngestionStatus`, analytics DTOs. Export JSON Schema dump for reference.
- **`libs/rag/`**: package foundation only — `Settings` (pydantic-settings), `log` (structlog), `exceptions` (typed hierarchy). RAG modules (`db`, `chunking`, `embeddings`, `vectorstore`, `retriever`, `rerank`, `pipeline`) are created in **P3** when implemented — kept out of P1 to avoid premature `NotImplementedError` stubs (YAGNI).
- **App stubs**: `apps/ingestion`, `apps/chat`, `apps/analytics` each a FastAPI app with `/health` + `Settings`; `apps/web` pnpm + Vite + TS + Tailwind config with a placeholder page.
- **`infra/postgres/init.sql`**: schema above (corrected DDL).
- **`docker-compose.yml`**: postgres + redis + four placeholder services with healthchecks and a shared network.
- **CI** (`.github/workflows/ci.yml`): jobs for `ruff check`, `mypy`, `pytest`, and web `eslint`/`tsc`. Must live under `.github/workflows/` for GitHub to discover it.
- **Verification**: `docker compose up` healthy; `uv run ruff check`, `uv run mypy`, `uv run pytest` (empty) and web `pnpm lint`/`tsc` all green; psql shows extension + tables.
