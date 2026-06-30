# Evaluation harness (`eval/`)

Offline RAGAS evaluation over a curated golden question set. Calls the same
guardrail, retrieval, and generation stack as `apps/chat` (no HTTP mocking).

## Prerequisites

- Postgres with the sample corpus indexed (`corpus.sample.json` is committed at
  the repo root).
- `OPENAI_API_KEY` in the environment (guardrail, embeddings, generation, RAGAS).

```bash
# One-time ingest (or upload via the web UI)
DATABASE_URL=postgresql+psycopg://abb:abb@localhost:5432/abb_rag \
  uv run python scripts/verify_rag.py

# Full eval (RAGAS + guardrail)
uv run abb-eval --corpus corpus.sample.json

# Guardrail-only (no RAGAS cost)
uv run abb-eval --skip-ragas
```

Reports land in `eval/results/` as paired JSON + Markdown files.

## Golden set

`abb_eval/golden_set.json` — ~28 items spanning AZ/EN/RU answerable banking
questions plus deliberate off-topic and injection probes for guardrail scoring.

## Metrics

| Category | Metrics |
| --- | --- |
| RAGAS | faithfulness, answer_relevancy, context_precision, context_recall |
| Guardrail | precision / recall on off-topic + injection items |
| Operational | avg / p95 latency per item (in report) |
