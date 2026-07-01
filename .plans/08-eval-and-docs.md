---
phase: P8
title: Evaluation & Documentation
depends_on: [P3, P4, P7]
enables: []
status: done
---

# P8 — Evaluation & Documentation

Prove the system's quality with a RAGAS evaluation harness and deliver the
documentation + demo materials. This is the strongest senior-engineer signal
(measuring quality, not asserting it) and directly serves the Documentation
scored criterion.

## Decisions

1. **RAGAS as the evaluation framework**
   - Decision: Use **RAGAS** (Python) over a curated golden question set to score **faithfulness, answer relevancy, context precision, context recall**.
   - Rationale: Decision 8; industry-standard RAG eval; native to the chosen Python stack; produces defensible numbers for the demo.

2. **Golden set authored from the corpus**
   - Decision: 28 QA pairs spanning AZ/EN/RU, individuals/business/about segments, plus 6 off-topic and 4 injection probes for guardrail precision/recall.
   - Rationale: Coverage of the real surface; tests both retrieval and refusal behavior against `corpus.sample.json`.

3. **Eval runs offline against the real pipeline**
   - Decision: Harness calls the same guardrail + `libs/rag` retrieval + chat generation path (no HTTP mocking), records metrics to JSON + markdown under `eval/results/`.
   - Rationale: Measures what ships; report is a committed artifact (`baseline.*` after first run).

4. **Documentation: layered (root + per-service + demo)**
   - Decision: Root README, `ARCHITECTURE.md`, `DEMO.md`, per-service READMEs (including analytics), `.env.example` kept in sync.
   - Rationale: Brief requires documentation + a live demo; layered docs serve both reviewers and presenters.

## Implemented

### Eval harness (`eval/`) ✅
- `abb_eval/golden_set.json` — `{ id, question, language, ground_truth?, kind }`.
- `abb_eval/runner.py` — per item: `auto_language` → `classify` → retrieve → `stream_answer` (or refusal).
- `abb_eval/report.py` — JSON + Markdown reporters; guardrail + latency stats.
- `uv run abb-eval` CLI; `--corpus` optional ingest, `--skip-ragas` for guardrail-only runs.
- Tests: golden set schema + guardrail metric unit tests (no OpenAI in CI).

### Metrics reported
- RAGAS: faithfulness, answer relevancy, context precision, context recall (answerable items only).
- Guardrail: off-topic + injection precision/recall.
- Operational: avg / p95 latency per item in the report.

### Documentation deliverables ✅
- **`README.md`** — quickstart, architecture summary, P1–P8 status.
- **`ARCHITECTURE.md`** — service boundaries, data flow, retrieval pipeline, schema.
- **`DEMO.md`** — live demo script with sample-corpus fallback.
- **`apps/analytics/README.md`** — endpoint + cache documentation.
- **`eval/README.md`** — harness usage.

### Platform context reflected in docs
- Per-question language auto-detect (`apps/chat/abb_chat/lang_detect.py`).
- Analytics: 4 charts + KPI cards, Redis minute-keyed cache, performance scoped to answered turns.
- Rate limit: POST-only, `DEFAULT_RATE_LIMIT_PER_MINUTE=10`, degrades if Redis down.
- Frontend: hand-written Zod schemas (not orval); demo fallback `corpus.sample.json`.

## Verification

- [x] `uv run pytest` includes eval tests
- [x] `uv run abb-eval --skip-ragas` runs without RAGAS API cost
- [x] Full RAGAS baseline committed — [`eval/results/baseline.md`](../eval/results/baseline.md) (2026-07-01, prod rerank + `corpus.sample.json`)
- [x] DEMO.md walkthrough matches current UI and API ports
