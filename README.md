# ABB RAG — Conversational AI over ABB Bank's website

A production-grade Retrieval-Augmented Generation (RAG) platform that scrapes ABB
Bank's official website, indexes it into a vector database, answers user questions
through a grounded, streaming chat interface, persists every interaction, and
visualizes usage analytics — all containerized for one-command deployment.

> Built for the "Data Extraction, Conversational AI, and Visualization" case study.
> Design decisions and phase plans live in [`.plans/`](.plans/); coding conventions
> in [`CONVENTIONS.md`](CONVENTIONS.md). Full scope record: [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md).

## Architecture

```
scraper (CLI)  ──►  corpus.json  ──►  upload (browser/localforage)
                                         │
                                         ▼
   ingestion-service ──► arq worker ──► Postgres + pgvector
                                         ▲
   chat-service  ◄── SSE ──► web SPA     │   (chunks · embeddings · chat_logs)
        │  retrieve → rerank → gpt-4o    │
        └──────────────────────────────► Postgres
   analytics-service ──► dashboard (recharts)
```

- **chat-service** is the brief's "microservice for question handling and response
  generation" (JSON contract `ChatRequest → ChatResponse`, streamed via SSE).
- **ingestion-service** + arq worker chunk and embed the uploaded corpus.
- **analytics-service** aggregates `chat_logs` for the dashboard.

| Component | Stack |
| --------- | ----- |
| Backend | Python 3.12, FastAPI, LangChain (LCEL), Pydantic v2, async SQLAlchemy |
| Vector store | Postgres 16 + pgvector (HNSW) + `unaccent` + `pg_trgm` |
| Embeddings / LLM | OpenAI `text-embedding-3-large` · `gpt-4o` / `gpt-4o-mini` |
| Rerank | local BGE cross-encoder (`bge-reranker-v2-m3`) |
| Queue / cache | Redis + arq |
| Scraper | Playwright (headless) + trafilatura |
| Frontend | Vite + React 19 + TS, Tailwind + shadcn/ui, recharts, localforage, TanStack Query |

## Quickstart

```bash
cp .env.example .env          # add your OPENAI_API_KEY
docker compose up --build     # postgres, redis, ingestion, worker, chat, analytics, web
```

Then open the web app, upload a `corpus.json` (generate one with the scraper, or use
the committed sample), wait for indexing, and start asking questions about ABB.

- **Port clash:** if a native Postgres already uses `5432`, set `POSTGRES_HOST_PORT=5433`
  in `.env` (container-internal wiring is unaffected).
- **Reranking (optional):** hybrid search answers well on its own and is the default.
  To enable the local BGE reranker, build the chat image with `INSTALL_RERANK=true`
  and set `RERANK_ENABLED=true` — best on GPU (CPU rerank is slow).
- **Manual API testing:** each service serves Swagger at `/docs` (`:8001` ingestion,
  `:8002` chat, `:8003` analytics). `POST /chat` is an SSE stream — use `curl -N` to
  see live tokens.

### Generate a corpus (the scraper "script")

```bash
uv run abb-scrape --out corpus.json        # one command in → corpus.json out
```

## Local development

```bash
uv sync                                     # install all Python workspace members
uv run ruff check . && uv run mypy . && uv run pytest
pnpm --dir apps/web install && pnpm --dir apps/web dev
```

## Repository map

| Path | Purpose |
| ---- | ------- |
| `packages/contracts/` | Pydantic v2 boundary models (single source of truth) |
| `libs/rag/` | Shared RAG core: chunking, embeddings, pgvector, retrieval, rerank |
| `apps/ingestion/` · `apps/chat/` · `apps/analytics/` | FastAPI microservices |
| `apps/scraper/` | Playwright crawler → `corpus.json` |
| `apps/web/` | React SPA (upload, chat, dashboard) |
| `infra/` | `postgres/init.sql`, CI workflows |
| `eval/` | RAGAS evaluation harness, golden set, [baseline results](eval/results/README.md) |

## Database volume

The Postgres schema is applied once by `init.sql` when the Docker volume is
first created. If you have a volume from an earlier build (before the
`chat_logs.status` CHECK constraint was added), recreate it so the constraint
takes effect:

```bash
docker compose down -v   # drops the postgres volume
docker compose up -d     # re-creates it and re-applies init.sql
```

Re-ingest your corpus after recreating the volume.

## Status

**P1–P8 complete.** Scraper → `corpus.json` (P2), `libs/rag` retrieval core (P3),
three FastAPI microservices with SSE chat, guardrails, async ingestion, and analytics
(P4), React SPA with upload, streaming chat, and i18n (P5), recharts dashboard (P6),
containerization with Redis POST-only rate limiting + CI image builds (P7), and RAGAS
eval harness plus architecture/demo docs (P8). See [`.plans/00-master-plan.md`](.plans/00-master-plan.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md), and [`DEMO.md`](DEMO.md).
