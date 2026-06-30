# ingestion-service (`apps/ingestion`)

FastAPI service that accepts an uploaded corpus and indexes it asynchronously via
an [arq](https://arq-docs.helpmanual.io) worker. Satisfies the brief's "format
extracted data into a vector database" (2b) through the async indexing path.

## Endpoints

| Method | Path | Body / Params | Returns |
| --- | --- | --- | --- |
| `POST` | `/ingest` | `IngestionRequest { corpus }` | `IngestionJob { job_id, state }` |
| `GET` | `/ingest/{job_id}` | — | `IngestionStatus { job_id, state, processed, total, error? }` |
| `GET` | `/health` | — | `{ status, service }` |

`POST /ingest` validates the corpus, enqueues an arq job on Redis, and returns a
`job_id` immediately (embedding a full site is minutes-long). The frontend polls
`GET /ingest/{job_id}` for progress.

## How it works

```
POST /ingest → validate Corpus → redis.enqueue_job → IngestionJob(queued)
arq worker  → ingest_corpus(corpus, on_progress) → progress hash in Redis
GET /ingest/{job_id} → read progress hash → IngestionStatus
```

- The worker calls `libs/rag.ingest_corpus`, which owns its own DB transactions
  (read hashes → embed outside a txn → per-document write) and is idempotent on
  `content_hash` (re-uploading the same corpus is a no-op).
- Progress (`state`, `processed`, `total`, `error`) lives in a Redis hash
  (`ingest:progress:{job_id}`), written by the worker and read by the API.

## Environment

`OPENAI_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `EMBEDDING_MODEL`/`EMBEDDING_DIM`,
`CORS_ORIGINS` (see root `.env.example`).

## Run

```bash
# API
uv run uvicorn abb_ingestion.main:app --port 8001
# Worker (separate process / container)
uv run arq abb_ingestion.worker.WorkerSettings
```

Both run as their own containers in `docker-compose.yml` (`ingestion` + `worker`,
same image).
