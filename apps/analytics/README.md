# analytics-service (`apps/analytics`)

FastAPI service that aggregates persisted `chat_logs` for the dashboard SPA.
Read-only — no writes to the corpus or chat tables beyond SELECT queries.

## Endpoints

| Method | Path | Returns |
| --- | --- | --- |
| `GET` | `/analytics/summary` | KPI cards (sessions, questions, answer rate, avg latency) |
| `GET` | `/analytics/volume` | Question volume time series (`bucket=hour\|day`) |
| `GET` | `/analytics/languages` | Question counts by detected language |
| `GET` | `/analytics/segments` | Citation counts by corpus segment |
| `GET` | `/analytics/performance` | Latency percentiles (answered turns only) |
| `GET` | `/analytics/top-questions` | Most frequent questions |
| `GET` | `/health` | `{ status, service }` |

Performance KPIs and latency charts scope to `status='answered'` so declined
guardrail turns do not skew operational metrics.

## Caching

Responses are cached in Redis with keys truncated to the minute (see
`abb_analytics/cache.py`). Cache is best-effort — if Redis is down the service
falls back to live SQL.

## Environment

`DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS` (see root `.env.example`).

## Run

```bash
uv run uvicorn abb_analytics.main:app --reload --port 8003
```

Swagger: http://localhost:8003/docs
