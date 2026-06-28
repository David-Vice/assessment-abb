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

## Decisions

1. **One image per service, multi-stage builds**
   - Decision: Separate Dockerfiles for `ingestion`, `chat` (+ worker, same image different command), `analytics`, `web`. Multi-stage: builder (uv/pnpm install) → slim runtime.
   - Rationale: True microservice packaging; small images; independent rebuilds.

2. **`docker compose` as the canonical deployment**
   - Decision: `docker-compose.yml` orchestrates postgres, redis, the services, the worker, and web (served via nginx static build). Healthchecks + depends_on ordering + named volumes.
   - Rationale: Brief asks for a portable Docker deployment; compose is the right scope for one week.

3. **BGE reranker model baked or cached at build**
   - Decision: Pre-download the reranker into the chat image layer (or a shared model volume) so first request isn't slow and runtime needs no model download.
   - Rationale: Predictable latency; offline-capable runtime.

4. **Redis token-bucket rate limiting**
   - Decision: Middleware on chat + ingestion (per-IP/session), limits from env.
   - Rationale: Decision 8; security awareness; protects OpenAI spend.

5. **CI completes the quality gate**
   - Decision: GitHub Actions: lint (ruff/eslint) → type (mypy/tsc) → test (pytest with pg+redis service containers; vitest) → build all images. PR-blocking.
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
- **Rate limiting**: shared middleware in a small lib, wired into chat + ingestion; env-configurable limits.
- **Model caching**: build step to pre-fetch BGE reranker; mount `model_cache`.
- **CI** (`.github/workflows/ci.yml`): lint/type/test jobs with postgres+redis services; image build job; cache uv/pnpm.
- **Docs**: root README "Run with Docker" section; troubleshooting (ports, model download, OpenAI key).
- **Verification**: fresh clone → `cp .env.example .env` (set OPENAI key) → `docker compose up` → full flow works end-to-end (upload→ingest→chat→dashboard); rate limit returns 429 past threshold; CI green on a test PR.
