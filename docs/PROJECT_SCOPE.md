# ABB RAG Platform — Project Scope & Engineering Record

This document is the **single walkthrough guide** for what was built, how it was
built, and the engineering decisions behind it. It maps the assessment brief to
implementation, lists features beyond the brief, and records UI/UX, ops, and
quality practices.

**Related docs:** [README](../README.md) · [ARCHITECTURE](../ARCHITECTURE.md) ·
[DEMO](../DEMO.md) · [Master plan](../.plans/00-master-plan.md) ·
[Eval baseline](../eval/results/README.md)

---

## 1. Assessment brief — coverage matrix

| Brief requirement | Implementation | Where to demo |
| --- | --- | --- |
| Web scraping | Playwright + trafilatura CLI → `corpus.json` | `uv run abb-scrape` or `corpus.sample.json` |
| Upload → browser storage | localforage (IndexedDB) on upload | Upload tab |
| OpenAI + vector DB | `text-embedding-3-large` → pgvector HNSW | Ingest + chat |
| Chat in ABB context | RAG + guardrail + citations | Chat tab |
| Microservices + JSON | chat / ingestion / analytics FastAPI | Swagger `:8001–8003` |
| Store Q/A + timestamps | `chat_logs` table | Dashboard + Postgres |
| Visualization | analytics-service + recharts | Dashboard tab |
| Docker | `docker compose up` full stack | `docker compose ps` |

**Verdict:** All mandatory requirements are implemented and E2E-demoable.

---

## 2. Phase plan (P1–P8)

Work was executed as eight phases documented in [`.plans/`](../.plans/):

| Phase | Focus | Status |
| --- | --- | --- |
| P1 | Monorepo, contracts, tooling, CI scaffold | ✅ |
| P2 | Playwright scraper → multilingual `corpus.json` | ✅ |
| P3 | `libs/rag`: chunk, embed, hybrid retrieve, rerank | ✅ |
| P4 | Three FastAPI services, SSE chat, arq worker, guardrail | ✅ |
| P5 | React SPA: upload, streaming chat, i18n | ✅ |
| P6 | Analytics API + recharts dashboard | ✅ |
| P7 | Docker, rate limiting, CI smoke, Redis persistence | ✅ |
| P8 | RAGAS eval harness, ARCHITECTURE.md, DEMO.md | ✅ |

**Execution discipline:** Day-2 gate required a thin E2E slice + green `docker compose up`
before advanced layers (rerank, RAGAS, i18n). Each advanced feature is independently
droppable (e.g. `RERANK_ENABLED=false`, eval in separate profile).

---

## 3. Technology stack

### Backend

| Layer | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12 | Assessment ecosystem, async RAG libs |
| API | FastAPI | OpenAPI-native, async, SSE |
| RAG | LangChain LCEL + custom SQL retriever | Flexibility for hybrid pgvector search |
| Contracts | Pydantic v2 (`packages/contracts`) | Single source of truth across services |
| Vector DB | Postgres 16 + pgvector (HNSW) | Vectors + chat logs in one ACID store |
| Sparse search | `pg_trgm` + `unaccent` | Equal AZ/EN/RU keyword path |
| Queue | Redis + arq | Async ingestion, progress, rate limits |
| Embeddings | OpenAI `text-embedding-3-large` | Multilingual retrieval quality |
| Chat LLM | `gpt-4o` + `gpt-4o-mini` (env-driven) | Flagship answers + cheap aux tasks |
| Rerank (optional) | BGE `bge-reranker-v2-m3` | Local cross-encoder, no extra API cost |
| Scraper | Playwright + trafilatura | ABB site is JS-rendered (Next.js) |
| Tooling | uv workspaces, ruff, mypy, pytest | Monorepo + strict CI |

### Frontend

| Layer | Choice | Why |
| --- | --- | --- |
| Framework | Vite + React 19 + TypeScript | Fast dev, modern SPA |
| Styling | Tailwind CSS + shadcn/ui patterns | Consistent design system |
| State | Zustand (persisted) + TanStack Query | UI prefs + server cache |
| Streaming | `@microsoft/fetch-event-source` | SSE from chat service |
| Validation | Hand-written Zod (`lib/schemas.ts`) | Mirrors Pydantic contracts |
| Storage | localforage | Corpus staging (IndexedDB) |
| Charts | recharts | Dashboard visualizations |
| i18n | i18next (AZ / EN / RU) | Matches bank's trilingual site |

### Infrastructure

| Component | Choice |
| --- | --- |
| Containers | Multi-service Docker Compose |
| DB init | `infra/postgres/init.sql` (no Alembic — demo scope) |
| CI | GitHub Actions: lint, mypy, pytest, pg+redis services, Docker smoke |
| Eval | Separate `eval` profile on chat image |

---

## 4. Architecture patterns

### Microservice boundaries

```
scraper (CLI) → corpus.json
       ↓
web (upload) → ingestion:8001 → arq worker → Postgres
       ↓
web (chat)  → chat:8002 → OpenAI + Postgres retrieve → SSE
       ↓
web (dash)  → analytics:8003 → Postgres aggregates
```

- **chat-service** is the brief's mandated “question handling & response generation”
  microservice (`ChatRequest` → streamed `ChatResponse`).
- **ingestion** + **worker** split HTTP from long-running embed/index work.
- **analytics** is read-only over `chat_logs` — no write path to RAG.

### Shared core (`libs/rag`)

One retrieval brain imported by chat, ingestion, and eval — avoids drift between
indexing and querying.

### Contract-first API

`packages/contracts` defines corpus, chat, ingestion, analytics models. Frontend
Zod schemas are kept aligned manually (same field names and enums).

### Async ingestion

`POST /ingest` returns `job_id` immediately; frontend polls `GET /ingest/{id}`.
Progress stored in Redis hashes before worker runs (race-safe init).

### Streaming + audit

Chat uses SSE (`token` events + terminal `done`). `asyncio.shield` persists partial
answers on client disconnect — audit trail survives errors.

---

## 5. RAG pipeline (quality features)

| Step | Implementation |
| --- | --- |
| Chunking | Language-aware splits in `libs/rag/chunking.py` |
| Dedup | Content-hash skip on re-ingest |
| Dense search | pgvector cosine, HNSW index |
| Sparse search | `simple` + `unaccent` + `pg_trgm` (no AZ stemmer bias) |
| Fusion | Reciprocal Rank Fusion (RRF) |
| Rerank | Optional BGE cross-encoder (`RERANK_ENABLED`) |
| Context budget | Token-limited packing before LLM |
| Citations | Chunk URL + title + snippet in response |
| Memory | Recent turns loaded for query rewrite (follow-ups) |
| Language | Per-question `py3langid` detect; answer in question language |

### Safety

| Control | Behavior |
| --- | --- |
| Guardrail (mini LLM) | `on_topic` / `off_topic` / `injection`; fail-closed on garbled labels |
| Social openers | “Hi”, “Salam”, etc. → welcome message (no false off-topic) |
| Prompt injection | Context delimited with random sentinel; system prompt never from corpus |
| Markdown render | `rehype-sanitize` on assistant output |
| Rate limit | Redis per-IP on POST only; socket IP (no XFF spoof); fail-closed default |
| SQL | Parameterized queries; sanitized client errors |

---

## 6. Frontend features & UX

### Screens

| Screen | Features |
| --- | --- |
| **Upload** | Drag-drop `corpus.json`, Zod validation, localforage save, progress polling |
| **Chat** | SSE streaming, citations panel, suggested prompts, new session, social welcome |
| **Dashboard** | KPI cards, volume/quality/distribution/top-questions charts, date + language filter |

### ABB brand alignment

- Official ABB SVG logo from abb-bank.az (`assets/abb-logo.svg`, `abb-mark.svg`)
- ABB primary blue (`hsl(212 100% 36%)`), Inter font, slogan *Modern · Useful · Universal*
- “ABB AI Assistant” + Beta badge in header
- Gradient user bubbles; card-style assistant messages

### AI assistant UX conventions (applied)

| Pattern | Implementation |
| --- | --- |
| Capability transparency | “Can / cannot” cards on empty chat |
| Suggested prompts | Full-width pills on mobile; pill chips on desktop |
| Trust disclaimer | Footer under chat input |
| Source citations | Expandable panel with deep links |
| Streaming indicator | Bouncing dots + status text |
| Accessibility | `role="log"`, `aria-live`, focus rings, 44px touch targets |
| Reduced motion | `prefers-reduced-motion` in CSS |

### Responsive design

Breakpoints (Tailwind): `xs` 400px · `sm` 640px · `md` 768px · `lg` 1024px

| Concern | Approach |
| --- | --- |
| Viewport height | `100dvh` + `.abb-app-shell` (mobile browser chrome) |
| Safe areas | `env(safe-area-inset-*)` for notched phones |
| Header | Icon-only nav on mobile; labels from `sm`; shortened title below 400px |
| Chat width | Shell: full → `max-w-2xl` (sm) → `max-w-3xl` (md) → `max-w-4xl` (lg) |
| Messages | `max-w-[92%]` mobile → `78%` desktop |
| Dashboard KPIs | 2 cols mobile → 3 tablet → 6 desktop |
| Charts | Single column mobile → 2-column grid `lg` |
| Filters | Stacked full-width buttons mobile → inline desktop |
| Input bar | Sticky bottom with backdrop blur + safe-area padding |

**Test:** Resize browser or use DevTools device toolbar (iPhone, iPad, desktop).

---

## 7. Ops, reliability & CI

| Item | Detail |
| --- | --- |
| Rate limiting | Per-IP POST cap; CORS outermost (429 visible in browser) |
| Redis | AOF persistence volume; queue + progress + rate limits |
| Ingestion cap | 50 MB `Content-Length` limit |
| Container hygiene | non-root users, `init: true`, healthchecks, `service_healthy` deps |
| CI backend | ruff, mypy, pytest with Postgres + Redis service containers |
| CI docker | `cp .env.example .env` + `compose up --wait` smoke |
| Eval | RAGAS 0.4.3 pinned; golden set 28 items AZ/EN/RU; baseline committed |

### Documented production gaps (out of scope)

Auth/SSO, Alembic migrations, Sentry/OTel, cloud deploy, PII redaction, corpus
reference storage (vs full payload in Redis queue).

---

## 8. Evaluation & quality metrics

**Harness:** `eval/` package — runs real stack (ingest → retrieve → generate → RAGAS).

**Baseline** (prod rerank, `corpus.sample.json`):

| Metric | Score |
| --- | --- |
| faithfulness | 0.773 |
| answer_relevancy | 0.690 |
| context_precision | 0.875 |
| context_recall | 0.857 |
| guardrail precision / recall | 0.714 / 1.000 |
| latency avg / p95 | ~12s / ~34s |

See [eval/results/baseline.md](../eval/results/baseline.md).

---

## 9. Engineering practices

From [CONVENTIONS.md](../CONVENTIONS.md):

- Pydantic at every boundary; no schema duplication
- Immutability-first; pure helpers without side effects
- Fail loud (worker re-raises; RAGAS exits non-zero on empty scores)
- Strict typing (mypy strict); ruff lint + format in CI
- Tests prove behavior (128+ backend, 16 frontend)
- Minimal diffs (YAGNI); reuse `libs/rag` and contracts

---

## 10. Repository map

```
abb-rag/
├── apps/
│   ├── scraper/      # Playwright CLI
│   ├── ingestion/    # POST /ingest + arq worker
│   ├── chat/         # SSE /chat + guardrail
│   ├── analytics/    # Dashboard API
│   └── web/          # React SPA
├── libs/rag/         # Shared RAG core
├── packages/contracts/
├── eval/             # RAGAS + golden set
├── infra/postgres/   # init.sql
├── .plans/           # P1–P8 phase plans
├── docs/             # This file
├── ARCHITECTURE.md
├── DEMO.md
└── docker-compose.yml
```

---

## 11. Demo checklist

```bash
cp .env.example .env          # set OPENAI_API_KEY
docker compose up --build -d
open http://localhost:5173
```

1. Upload `corpus.sample.json` → wait for **completed**
2. Chat: loan question (EN), miles promo (AZ), off-topic decline
3. Dashboard: volume + quality charts
4. Optional: `docker compose --profile eval run --rm eval --corpus corpus.sample.json`

---

## 12. Summary

This project delivers a **complete assessment solution** plus production-minded
extras: hybrid multilingual RAG, guardrails, streaming audit trail, analytics,
RAGAS eval, rate limiting, CI smoke tests, and an ABB-branded responsive SPA.
The phase plan in `.plans/` drove systematic delivery; `libs/rag` and
`packages/contracts` keep the architecture coherent as features were added.
