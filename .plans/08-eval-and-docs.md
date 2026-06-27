---
phase: P8
title: Evaluation & Documentation
depends_on: [P3, P4, P7]
enables: []
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
   - Decision: ~25–40 QA pairs spanning AZ/EN/RU, all segments, plus deliberate off-topic probes for guardrail precision.
   - Rationale: Coverage of the real surface; tests both retrieval and refusal behavior.

3. **Eval runs offline against the real pipeline**
   - Decision: Harness calls the same `libs/rag` retrieval + the chat generation path (no mocking the RAG), records metrics to JSON + a markdown report.
   - Rationale: Measures what ships; report is a committed artifact.

4. **Documentation: layered (root + per-service + demo)**
   - Decision: Root README (vision, architecture, quickstart), per-service READMEs (already seeded in earlier phases), an `ARCHITECTURE.md`, and a `DEMO.md` script for the ABB walkthrough.
   - Rationale: Brief requires documentation + a live demo; layered docs serve both reviewers and presenters.

## Plan

### Eval harness (`eval/`)
- `golden_set.json` — `{ question, language, ground_truth, expected_sources?, kind: "answerable"|"offtopic" }`.
- `run_eval.py` — for each item: retrieve → generate → collect (question, answer, contexts, ground_truth) → RAGAS metrics → aggregate.
- Outputs: `eval/results/<timestamp>.json` + `eval/results/<timestamp>.md` (per-question + aggregate table); guardrail precision/recall on off-topic items.
- `uv run abb-eval` script entry; optional CI job (non-blocking, artifact upload).

### Metrics reported
- Faithfulness, Answer Relevancy, Context Precision, Context Recall (RAGAS).
- Guardrail: off-topic detection precision/recall.
- Operational: avg/p95 latency, avg tokens/cost (pulled from `chat_logs`).

### Documentation deliverables
- **`README.md`** (root): what/why, architecture diagram, one-command quickstart, feature list, the 9 decisions summary, links to phase plans.
- **`ARCHITECTURE.md`**: service boundaries, data flow, retrieval pipeline, schema, sequence diagrams.
- **`DEMO.md`**: step-by-step live demo script (scrape → upload → ingest → ask 3 scripted questions incl. off-topic + multilingual → show citations → show dashboard → show eval report), with fallback notes (use committed sample corpus).
- Per-service READMEs verified complete.

## Breakdown

- **Golden set**: author QA pairs from corpus across languages/segments + off-topic probes.
- **Harness**: `run_eval.py`, RAGAS integration, JSON+MD reporters, CLI entry, optional CI artifact job.
- **Run + record**: execute against the live stack; commit a baseline results report.
- **Docs**: root README, ARCHITECTURE.md, DEMO.md; verify per-service READMEs; ensure `.env.example` fully documented.
- **Final QA pass**: walk the DEMO.md end-to-end on a clean machine/container; fix any gaps; confirm Definition of Done (master plan §8).
- **Verification**: eval report generated with real scores; demo script runs start-to-finish via `docker compose up`; all CI green.
