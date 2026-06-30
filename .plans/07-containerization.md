---
phase: P7
title: Containerization — Docker, Compose, Rate Limiting, CI
depends_on: [P4, P5, P6]
enables: [P8]
---

# P7 — Containerization & Ops

Package everything for one-command deployment, add Redis-backed rate limiting,
and complete the CI pipeline. Satisfies brief requirement 4 (Docker) and the
Efficiency / Code Quality criteria.

> **Status:** ✅ done. Image/compose foundation landed early during P4; P7 added
> Redis-backed per-IP rate limiting on chat + ingestion, CI service containers
> (Postgres + Redis + `init.sql`), a `docker compose build` job, and synced docs.

## Decisions

1. **One image per service, multi-stage builds**
   - Decision: Separate Dockerfiles for `ingestion`, `chat` (+ worker, same image different command), `analytics`, `web`. Multi-stage: builder (uv/pnpm install) → slim runtime.
   - Rationale: True microservice packaging; small images; independent rebuilds.

2. **`docker compose` as the canonical deployment**
   - Decision: `docker-compose.yml` orchestrates postgres, redis, the services, the worker, and web (served via nginx static build). Healthchecks + depends_on ordering + named volumes.
   - Rationale: Brief asks for a portable Docker deployment; compose is the right scope for one week.

3. **BGE reranker model baked at build, loaded offline** ✅ done
   - Decision: When `INSTALL_RERANK=true`, pre-download the reranker in a layer **before** the app-source COPY (so code edits don't re-trigger it), and run with `HF_HUB_OFFLINE=1` so the runtime never contacts the Hub. Default build is lean (no torch).
   - Rationale: Predictable latency, offline runtime, fast rebuilds. Industry best practice for a ~600 MB model is bake-into-image (vs runtime download) — validated against AWS EKS AI/ML guidance.
   - Note: the cross-encoder is CPU-bound; on CPU, latency scales with `RETRIEVAL_CANDIDATES`. Default ships rerank off; enable on GPU for production.

6. **Graceful shutdown** ✅ done
   - Decision: Exec the server/worker binary directly as PID 1 (`/app/.venv/bin/uvicorn|arq`, not `uv run`), plus `init: true` (tini) and `stop_grace_period` per service.
   - Rationale: `uv run` as PID 1 swallowed SIGTERM, forcing ~150s SIGKILL waits on `compose down`. Exec-form + tini delivers the signal so uvicorn/arq stop in ~1s.

4. **Redis token-bucket rate limiting** ✅ done
   - Decision: `RateLimitMiddleware` on chat + ingestion — **POST only** (chat
     messages + corpus upload starts). GET polling and session hydration are excluded.
     Per-IP fixed 60s window; default `DEFAULT_RATE_LIMIT_PER_MINUTE=10` in
     `libs/rag/abb_rag/settings.py`, overridable via `RATE_LIMIT_PER_MINUTE`.
     Skips `/health`; degrades gracefully if Redis is unavailable.
   - Rationale: Decision 8; protects OpenAI spend without breaking ingestion polling.

5. **CI completes the quality gate** ✅ done
   - Decision: GitHub Actions: lint (ruff/eslint) → type (mypy/tsc) → test (pytest with pg+redis service containers + `init.sql`; vitest) → `docker compose build`. PR-blocking.
   - Rationale: Code Quality is scored; prevents regressions.

## Plan

### Compose topology
```yaml
services:
  postgres:   # pgvector image + init.sql, volume, healthcheck
  redis:      # cache/queue/rate-limit, healthcheck
  ingestion:  # FastAPI; depends_on postgres+redis
  worker:     # arq; same image as ingestion, command=worker
  chat:       # FastAPI SSE; bundles reranker model
  analytics:  # FastAPI
  web:        # nginx serving Vite build; proxies /api/* to services (or direct CORS)
volumes: [pg_data, model_cache]
networks: [abb_net]
```

### Image strategy
- Python images: `uv` for deps in builder, copy venv to slim `python:3.12-slim`; non-root user; `EXPOSE` + uvicorn entry.
- Web image: pnpm build in node builder → static assets in nginx; runtime env injection for API base URLs.
- `.dockerignore` per app; pinned base images.

### Configuration
- Single `.env` consumed by compose; `.env.example` documents every key.
- Healthchecks gate readiness; restart policies set.

## Breakdown

- **Dockerfiles**: `apps/ingestion/Dockerfile`, `apps/chat/Dockerfile` (+ worker command), `apps/analytics/Dockerfile`, `apps/web/Dockerfile` (+ `nginx.conf`).
- **`docker-compose.yml`**: full topology above with healthchecks, depends_on, volumes, networks; optional `docker-compose.override.yml` for dev (hot reload, mounted source).
- **Rate limiting**: `libs/rag/abb_rag/rate_limit.py` middleware wired into chat + ingestion; env-configurable `RATE_LIMIT_PER_MINUTE`; unit + route tests.
- **Model caching**: build step to pre-fetch BGE reranker; mount `model_cache`.
- **CI** (`.github/workflows/ci.yml`): lint/type/test jobs with postgres+redis services + schema init; `docker` image-build job; cache uv/pnpm.
- **Docs**: root README "Run with Docker" section; troubleshooting (ports, model download, OpenAI key).
- **Verification**: fresh clone → `cp .env.example .env` (set OPENAI key) → `docker compose up` → full flow works end-to-end (upload→ingest→chat→dashboard); rate limit returns 429 past threshold; CI green on a test PR.
