# ABB RAG — Code-Writing Conventions

> Single source of truth for *how code is written* in this repo. Adapted from the
> TimeBack backend/frontend golden guidelines, translated to **idiomatic Python**
> for the FastAPI + LangChain backend (suffix-everywhere and NestJS-style DI are
> TypeScript-isms we deliberately avoid). Treat every Golden rule as a hard gate.

---

## 0. Stack in one paragraph

Monorepo. **Backend:** Python 3.12, FastAPI + LangChain (LCEL), Pydantic v2,
async SQLAlchemy + psycopg, Postgres 16 + pgvector, arq + Redis worker, managed by
**uv** workspaces. **Frontend:** Vite + React 19 + TypeScript, Tailwind + shadcn/ui,
TanStack Query, Zustand, recharts, localforage, pnpm. Shared Pydantic contracts →
OpenAPI → generated Zod schemas on the frontend. Everything Dockerized.

---

## 1. Golden rules (non-negotiable)

1. **Pydantic is the source of truth** at every boundary (API, settings, LLM I/O). Types flow from the model; never hand-duplicate a schema. SQLAlchemy models own persistence only.
2. **Immutability first.** Pure functions return new objects; never mutate inputs or shared state. Value objects use `frozen=True`. Side effects live at boundaries (repositories, clients), never in pure helpers.
3. **Pure helpers stay pure.** A function in a `utils`/pure module has no I/O, no logger, no service, no side effects. If it needs them, it's a service — model it as one.
4. **Fail loud.** Never swallow an error on a retryable path. Worker tasks re-raise so arq can retry/alarm. No `return {"success": True}` after catching a failure.
5. **Self-documenting, why-only comments.** Default to zero comments. A comment explains *why* (a constraint, trade-off, non-obvious decision) — never *what*. No planning-artifact refs (`# Decision 3`, `# per the plan`), no history breadcrumbs, no TODOs. Public functions/classes may carry a short docstring of intent.
6. **One module = one domain; stereotype = one directory.** Cross-package imports go through `abb_contracts` / `abb_rag`. Never reach into another app's internals.
7. **No `Any`, no silencing casts.** Use `typing.cast` only with justification. Let mypy enforce invariants.
8. **SCREAMING_SNAKE_CASE enums** — `enum.Enum` (or `StrEnum`), member names *and* values.
9. **Reuse before you write.** Search the repo + check stdlib/a library before hand-rolling. Extend existing utils/services; don't clone.
10. **Minimal, surgical changes (YAGNI).** No fields/abstractions "for later." Remove unused code.
11. **Tests prove behavior.** A test fails if behavior regresses (assert real, non-default values). AAA comments only.
12. **Every gate green locally** before commit: `uv run ruff check .`, `uv run mypy .`, `uv run pytest`, and (web) `pnpm lint && pnpm type-check && pnpm test`.

---

## 2. Backend layout (stereotype directories, pythonic names)

```
libs/rag/abb_rag/
  settings.py            # pydantic-settings (env-driven config)
  db.py                  # async engine/session + pool
  chunking.py            # pure: document -> chunks
  embeddings.py          # OpenAI embeddings client (retry)
  vectorstore.py         # pgvector upsert/query
  retriever.py           # hybrid dense+sparse + RRF
  rerank.py              # BGE cross-encoder (lazy, toggle)
  pipeline.py            # ingest_corpus() / retrieve() orchestration
  prompts/               # jinja prompt templates + loaders
  exceptions.py          # typed error hierarchy

apps/<service>/abb_<service>/
  main.py                # FastAPI app factory + lifespan
  config.py              # service Settings
  api/routers/*.py       # one router module per resource (chat, ingest, ...)
  api/dependencies.py    # FastAPI Depends providers
  services/*.py          # business logic (classes or functions)
  repositories/*.py      # DB access (async)

packages/contracts/abb_contracts/
  corpus.py  chat.py  ingestion.py  analytics.py   # Pydantic v2 boundary models
```

- Domain-named snake_case files inside stereotype directories (`services/chat.py`), **not** `chat_service.py` suffixes.
- Classes `PascalCase`; functions/modules `snake_case`; constants `SCREAMING_SNAKE_CASE` at file top.
- Public methods before private (`_private`) helpers.

## 3. Services & dependency injection

- **Request-scoped** deps (DB session, current settings, per-request services) via FastAPI `Depends`.
- **App-scoped singletons** (LLM client, embeddings client, DB engine, reranker) built in `lifespan` and stored on `app.state`; exposed through a `Depends` reader. No global DI container, no decorator magic.
- Services receive their deps explicitly (constructor or function args) so tests inject fakes.
- Side effects (DB, HTTP, OpenAI) only in repositories/clients/services — never in models or `__init__` import time.

## 4. Models (Pydantic v2)

- Boundary models in `packages/contracts`. `model_config = ConfigDict(extra="forbid")` on internal/outbound; allow extra only on ingress that must forward-compat.
- Enums via `enum.Enum`/`StrEnum`, referenced in models — no inline literal sets where an enum is reused.
- Map Pydantic ↔ SQLAlchemy explicitly (`Model.model_validate(row)`); don't conflate them.
- Frozen value objects where mutation is meaningless.

## 5. Errors

Typed hierarchy in `abb_rag/exceptions.py`; FastAPI exception handlers translate to JSON.

```python
class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

class NotFoundError(AppError): status_code = 404; code = "NOT_FOUND"
class ExternalServiceError(AppError): status_code = 502; code = "UPSTREAM_ERROR"
```

- Wrap OpenAI/LangChain/Redis failures in `ExternalServiceError` with safe messages.
- Retryable worker paths re-raise. Validate required config at startup (fail fast).
- Retry external calls with exponential backoff (`tenacity`), not hand-rolled loops.

## 6. Logging

- **structlog** JSON logging via a `get_logger(name)` helper. Never `print`.
- `info` at entry/success of key RAG events (ingest, retrieval count, LLM call: model, tokens, latency_ms); `warning` for recoverable anomalies (name the missing config); `error` in except blocks with structured context.
- Static message strings; variable data in structured fields. Never log secrets/PII/full prompts.
- Correlation/request id middleware so logs are traceable (observability is out-of-scope but the seams are real).

## 7. Async & immutability

- All route handlers and I/O `async def`; use `httpx.AsyncClient`, async SQLAlchemy, LangChain `ainvoke`/`astream`.
- No CPU-heavy work on the event loop — offload to the arq worker.
- Pure functions for transformations (chunk selection, fusion, mapping); `frozen=True` for value objects; no hidden global state.

## 8. Tests (pytest)

- `pytest` + `pytest-asyncio`. Files `test_<module>.py` under each package's `tests/`. Test names describe the outcome (no `should` prefix).
- **AAA comments only** in test bodies: `# Arrange` / `# Act` / `# Assert` (`# Arrange & Act` when inseparable).
- Fixtures for DB (transaction-rollback per test), `AsyncClient` app, Redis (fakeredis). External services behind interfaces with **fake implementations**; OpenAI/LangChain stubbed with deterministic fakes (`respx` for raw HTTP). Never hit the network.
- Test-data builder functions typed to the real model; no `Any`. Prove behavior with non-default values.
- Don't unit-test infra (compose/Dockerfiles).

## 9. Comments — same why-only policy as §1.5

Decide in order: better name/smaller function → "why" obvious from types → would a competent reader trip? → one concise `# why` comment, else none. Public API gets a one-line docstring of intent. No banners, no narration, no stale comments.

## 10. Tooling: ruff + mypy strict

- `ruff` (lint + format), `mypy --strict` with `plugins = ["pydantic.mypy"]`. No suppressions to pass CI — fix the code. Line length 100.
- Fully annotate public functions, FastAPI deps, route handlers, and models.

---

## 11. Frontend conventions (TypeScript — keep TS idioms)

- `<name>.<stereotype>.ts(x)` suffixes (`.component.tsx`, `.hook.ts`, `.store.ts`, `.selector.ts`, `.model.ts`, `.constant.ts`, `.util.ts`). Test co-located `<name>.test.ts(x)`.
- **No `any`.** Types in `model` files, not inlined. ALL-CAPS constants at file top.
- **Zod at runtime boundaries only** — generated from backend OpenAPI for API responses, hand-written only for the uploaded `corpus.json`. Validate (`.parse()`) at the boundary.
- State: Zustand for UI/app state (minimal, normalized); TanStack Query for server state. Components presentational; logic in hooks; `displayName` on memo/FC exports.
- i18n via i18next (`useTranslationForNs`) — AZ/RU/EN all first-class, no hardcoded user strings.
- Immutability; pure functions; side effects in hooks/query mutations, not components/selectors.
- why-only comments; Vitest AAA-only test comments, observable-outcome assertions.
- Tailwind classes ordered position → box → color/font; shadcn/ui for primitives.

---

## 12. CI gates (mirror locally before commit)

```bash
# backend
uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest
# frontend
pnpm --dir apps/web lint && pnpm --dir apps/web type-check && pnpm --dir apps/web test
```

No lint/type suppressions. `docker compose up` must stay green from the Day-2 de-risking gate onward.
