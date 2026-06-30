# Evaluation harness (`eval/`)

Offline RAGAS evaluation over a curated golden question set. Calls the same
guardrail, retrieval, and generation stack as `apps/chat` (no HTTP mocking).

## Prod-faithful eval (recommended)

Use this when `RERANK_ENABLED=true` in `.env` — same rerank stack as the chat
container (torch + BGE cross-encoder baked into the eval image).

```bash
docker compose --profile eval run --rm eval \
  --corpus /app/corpus.sample.json \
  --stem baseline

# or
bash scripts/run_eval_prod.sh --stem baseline
```

Reports are written to `eval/results/` on the host. Inside the container,
`DATABASE_URL` from `.env` already points at `postgres:5432` on the compose network.

Rebuild when `INSTALL_RERANK` or deps change:

```bash
docker compose --profile eval build eval
```

## Quick local eval (no rerank)

For a fast smoke test on the host venv **without** prod parity (hybrid search
only, no cross-encoder):

```bash
# Windows: use localhost:5433 if native Postgres occupies 5432
DATABASE_URL=postgresql+psycopg://abb:abb@localhost:5433/abb_rag \
  uv run abb-eval --no-rerank --stem baseline
```

Scores from `--no-rerank` runs are **not comparable** to production chat when
reranking is enabled there.

## Full local eval with rerank

Only if you install the rerank extra locally (heavy: pulls torch):

```bash
uv sync --package abb-chat --extra rerank
DATABASE_URL=postgresql+psycopg://abb:abb@localhost:5433/abb_rag \
  uv run abb-eval --stem baseline
```

## Golden set

`abb_eval/golden_set.json` — ~28 items spanning AZ/EN/RU answerable banking
questions plus deliberate off-topic and injection probes for guardrail scoring.

## Metrics

| Category | Metrics |
| --- | --- |
| RAGAS | faithfulness, answer_relevancy, context_precision, context_recall |
| Guardrail | precision / recall on off-topic + injection items |
| Operational | avg / p95 latency per item (in report) |
