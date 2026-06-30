# P4 — Backend API — Multi-Perspective Code Review

> Cross-validated review of the P4 microservices (`apps/chat`, `apps/ingestion`,
> `apps/analytics`) + the container/compose hardening and `libs/rag` changes P4
> introduced. Diff base: `88b0472` (P3 complete) → `HEAD`. Four isolated reviewers
> on different models, then an orchestrator audit that validated every load-bearing
> claim against the code, the live DB schema, the contracts, and external sources.

## Methodology

- **Reviewers (parallel, isolated, different models):** [Alpha](dd0d1be4-849f-4e0b-a7bf-53cc4cc5a1e7) (opus-max), [Beta](bb38699f-0c74-4010-8ffd-fa6553d907fb) (gpt-5.4), [Gamma](67b82362-6fd1-4d17-ab3f-57b85364b244) (composer-2), [Delta](3c27d467-00ee-491b-b274-84d2c5118c07) (sonnet).
- **Audit:** main agent — cross-validated findings against on-disk code, `init.sql`, contracts, and the P3 review; externally validated the evolving APIs (LangChain `stream_usage`, arq `_job_id`, `to_tsquery`/stopword behavior, guardrail fail-closed guidance) via Perplexity.
- **Gates:** `ruff check .` ✅ · `ruff format` ✅ · `mypy --strict` ✅ (70 files) · `pytest` ✅.

## Verdict

**Architecturally sound, E2E-functional microservice layer with no true Criticals.**
Disciplined design: shielded persist-on-disconnect, typed `ExternalServiceError` on
every OpenAI path, URL-deduped citations, fully parameterized SQL with the generated
`tsv` column never written, rerank offloaded via `asyncio.to_thread`, a correct arq
worker lifecycle, and prompt-injection defense with untrusted-context labeling. The
P1–P3 foundations it builds on are consistent.

The substantive work was a cluster of **HIGH** correctness/security/observability
issues with strong cross-model agreement. **All HIGHs and the high-value MEDIUMs
have been remediated** (below); gates re-run green.

## Remediation status (this pass)

| Finding | Models | Severity | Status |
| --- | --- | --- | --- |
| Guardrail fails **open** (unknown label → ON_TOPIC) | A·B·Γ·Δ | HIGH | ✅ Fail closed → `OFF_TOPIC`; test updated |
| Persistence failure swallowed → fake `chat_log_id=0` success | A·B·Γ·Δ | HIGH | ✅ `_persist` raises; success persists in `try`, failure emits `error`, no `done`; new test |
| Token usage never captured/persisted (breaks P6) | A·Γ·Δ (B:low) | HIGH | ✅ `stream_usage=True`; `TokenUsage` accumulated from final chunk; `prompt_tokens`/`completion_tokens` persisted; new test |
| SSE `done` in `finally` + `error`→`done` double terminal event | A·Γ·Δ | HIGH | ✅ `done` emitted only on success in `try`; `finally` only persists (no `yield`) |
| Ingestion progress race (enqueue before init) | A·B·Γ·Δ | HIGH | ✅ `init_progress` before enqueue with pre-generated `_job_id`; `set_state` clears stale error |
| Guardrail default + rerank-enabled default unsafe | B | MEDIUM | ✅ `rerank_enabled` defaults `False` (extra is opt-in) |
| Injection collapsed to `declined_off_topic` (no audit state) | A·Γ·Δ | MEDIUM | ✅ `AnswerStatus.DECLINED_INJECTION` + `init.sql` CHECK + verdict branch |
| Sparse FTS dead for NL queries (`websearch` ANDs stopwords) | A·Γ·Δ | MEDIUM | ✅ OR-of-terms `to_tsquery` (`_or_tsquery`), language-uniform; matches the `sparse=0` we observed |
| History not token-budgeted (Decision 8) | A·B·Γ·Δ | MEDIUM | ✅ `build_chat_messages` budgets history+system+question, trims oldest first |
| Upstream error detail leaked to client | A·Γ·Δ | MEDIUM | ✅ generic per-code public messages; raw detail logged only |
| Memory replays declined/error turns | B·Γ | MEDIUM | ✅ `load_history` filters to answered, non-empty turns |
| Redis/arq errors unwrapped in ingest router | A·Γ | MEDIUM | ✅ wrapped in `ExternalServiceError` |
| Escapable `<context>` delimiter | A·Γ·Δ | MEDIUM | ✅ random per-request sentinel; stray sentinel stripped from context |

### Deferred (documented, lower ROI / out of scope)

- **Ingestion/analytics Dockerfiles not layered + late `chown -R`** (A·B·Γ) — build-speed only; the chat image already uses the optimized pattern. P7 polish.
- **Full corpus through the Redis job payload** (A·Γ) — fine at demo scale; a staged-reference design is a production refinement.
- **`lru_cache` LLM singletons not built in `lifespan`** (A) — testable via `cache_clear()`; lifespan wiring is a refinement.
- **No fail-fast on empty `OPENAI_API_KEY` at startup** (A·Γ) — surfaces on first call; a startup validator would break key-less unit tests, so deferred to a guarded lifespan check.
- **`count_tokens` uses `cl100k_base`; gpt-4o uses `o200k_base`** (A·B·Γ·Δ low) — exact for embeddings; an estimate for the chat budget (acceptable margin).
- **`GET /sessions/{id}` has no access control** — auth is explicitly out of scope (master plan §8a).

## False positives (validated and dismissed)

- **`asyncio.shield` doesn't persist on disconnect (raised as possible Critical).** Gamma validated and the audit confirms: `shield` schedules the coroutine; on a genuine disconnect the `finally` awaits it normally. Persist-on-disconnect works (covered by `test_chat_persists_partial_answer_on_disconnect`).
- **`yield` in `finally` is a guaranteed crash.** It was fragile, not a guaranteed crash (guarded by `is_disconnected`). Resolved anyway by removing all `yield` from `finally`.
- **Worker image carries torch.** The worker uses the ingestion image, which does **not** install the `rerank` extra — no torch present. Non-issue.
- **`Row[Any]` everywhere violates "no Any".** Justified narrow exception for raw `text()` rows (consistent with the P3 review); SQL variables are typed `TextClause`, params `dict[str, object]`.

## Conventions compliance (`CONVENTIONS.md`)

| Area | Status | Note |
| --- | :-: | --- |
| Immutability (§2) | ✅ | frozen value objects; pure helpers; `replace()` |
| Fail loud (§1.4/§5) | ✅ | persistence now raises; OpenAI/Redis wrapped in typed errors |
| No `Any` (§1.7) | ✅ | only justified `Row[Any]`/arq `ctx`/redis-py `# type: ignore[misc]` |
| Async / no CPU on loop (§7) | ✅ | rerank off-loop; awaitable `ProgressCallback`; only trivial tiktoken on-loop |
| Logging (§6) | ✅ | structured info/error at key events |
| SQL vs `init.sql` | ✅ | parameterized; generated `tsv` never written; halfvec casts; `immutable_unaccent` match |
| Security (§24) | ✅ | injection-defended prompt (random sentinel), guardrail fail-closed, generic error detail, SecretStr, CORS |
| Tests prove behavior (§8/§11) | ✅ | happy/decline(off-topic+injection)/disconnect/citation-dedup/token-usage/persist-failure + ingestion lifecycle |
| ruff/mypy/format green (§10/§12) | ✅ | all green |

## End-to-end traces (verified)

**Chat SSE (`POST /chat`):** classify (fail-closed) → [decline → refusal] or [memory(answered-only) → rewrite → hybrid retrieve (dense + OR-sparse + RRF → optional off-loop rerank) → URL-deduped citations → budgeted context] → `gpt-4o` stream (token usage accumulated, disconnect-checked) → **success: persist (shielded) + single `done`**; **error: `error` only**; **disconnect/failure: `finally` persists (no yield)**. Terminal-event contract: exactly one of `done`/`error`.

**Ingestion (`POST /ingest` → worker → status):** init progress → enqueue with `_job_id` → worker `RUNNING` → `ingest_corpus` (read hashes → embed outside txn → per-doc commit, idempotent) → `COMPLETED`; failure → `set_failed` + re-raise (arq retry). `GET /ingest/{job_id}` → `IngestionStatus` / 404. Redis failures wrapped.

## Notes for deployment

- **`init.sql` gained `declined_injection`** in the `chat_logs` status CHECK. A DB created before this pass has the old constraint; persisting an injection-declined turn there would fail the CHECK. Recreate the volume **or** apply an additive `ALTER` widening the constraint (no data loss) before relying on injection logging on an existing DB.
- Chat/ingestion/analytics images must be rebuilt to pick up these code changes.

## Overall assessment

- **Merge readiness:** ready after the applied fixes; gates green.
- **Risk level:** low — no Criticals; all HIGHs remediated and covered by tests.
- **Confidence:** high — four independent models, code-level cross-validation, external validation of evolving APIs, and re-run gates.
