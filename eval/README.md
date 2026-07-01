# Evaluation harness (`eval/`)

Offline RAGAS evaluation over a curated golden question set. Calls the same
guardrail, retrieval, and generation stack as `apps/chat` (no HTTP mocking).

## Prod-faithful eval (recommended)

Reuses the **chat Docker image** (same rerank stack as production). The eval image
only adds `abb-eval` + RAGAS — no second torch/CUDA download.

```bash
docker compose build chat
docker compose --profile eval build eval   # ~1–3 min after chat exists

docker compose --profile eval run --rm eval \
  --corpus corpus.sample.json \
  --stem baseline

# or (builds chat + eval, then runs):
bash scripts/run_eval_prod.sh --stem baseline
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

## Baseline results (committed)

Prod-faithful run on `corpus.sample.json` with rerank + full RAGAS:

| Metric | Score |
| --- | ---: |
| faithfulness | 0.773 |
| answer_relevancy | 0.690 |
| context_precision | 0.875 |
| context_recall | 0.857 |
| guardrail precision / recall | 0.714 / 1.000 |
| latency avg / p95 | 12s / 34s |

Full reports: [`results/baseline.md`](results/baseline.md) ·
[`results/baseline.json`](results/baseline.json) ·
[`results/README.md`](results/README.md) (methodology and caveats).
