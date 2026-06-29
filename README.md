# ABB RAG — Conversational AI over ABB Bank's website

A production-grade Retrieval-Augmented Generation (RAG) platform that scrapes ABB
Bank's official website, indexes it into a vector database, answers user questions
through a grounded, streaming chat interface, persists every interaction, and
visualizes usage analytics — all containerized for one-command deployment.

> Built for the "Data Extraction, Conversational AI, and Visualization" case study.
> Design decisions and phase plans live in [`.plans/`](.plans/); coding conventions
> in [`CONVENTIONS.md`](CONVENTIONS.md).

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
| `eval/` | RAGAS evaluation harness + golden set |

## Status

Phase **P1 (Foundations)** — scaffolding in place. See [`.plans/00-master-plan.md`](.plans/00-master-plan.md)
for the full roadmap and the Day-2 de-risking gate.
