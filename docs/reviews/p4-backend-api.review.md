# P4 — Backend API — Multi-Perspective Code Review

> Cross-validated review of the three FastAPI services — **chat** (SSE, guardrail,
> memory, generation, citations, persistence), **ingestion** (arq worker, Redis
> progress), **analytics** (stub) — plus supporting `libs/rag` deltas. Diff base:
> committed `88b0472` (P3); P4 is uncommitted. Four isolated reviewers on different
> models + an orchestrator audit validated against the code, a live E2E (OpenAI +
> Postgres + the ingested sample), and an empirical async-generator repro.

## Methodology

- **Reviewers (parallel, isolated, different models):** [Alpha](2c0d38a8-b090-4b35-82a8-366a41f3aa40) (opus-max), [Beta](cd018145-6499-4c9a-a1f9-bb8a5755c670) (gpt-5.4), [Gamma](04331e20-86c9-4f10-b278-077a0e304e10) (composer-2), [Delta](7ca43b1a-1384-4972-a2f9-3a9b0ed3e1fd) (sonnet).
- **Gates:** `ruff` ✅ · `mypy --strict` ✅ · `pytest apps/chat apps/ingestion` ✅ (20).
- **Live E2E (`guardrail → retrieve → generate → persist`, real OpenAI + DB):** on-topic question → 6 chunks / 5 deduped citations → gpt-4o grounded answer (correctly declined to invent details absent from the sample) → **persisted (`chat_log_id`, citations round-tripped)**; off-topic → `off_topic`; "ignore all previous instructions" → `injection`. The full chat path works.

## Verdict

**Functionally complete and E2E-working, faithful to the plan, with no true Criticals** — both reviewer "Criticals" (the disconnect crash and the `retrieved_ids` cast) were disproven by direct testing. The architecture is strong: shielded persist-on-disconnect, typed errors on every OpenAI path, URL-deduped citations, correct arq lifecycle, parameterized SQL, injection-defended prompt. Real work: **3 High** (SSE terminal-event handling, token-usage persistence, silent persist-failure) and a set of Mediums. Address the High items before P5/P6 depend on this.

## Cross-model consensus matrix (top findings)

| Finding | Alpha | Beta | Gamma | Delta | Audit verdict |
| --- | :-: | :-: | :-: | :-: | --- |
| `done` yielded in `finally` + `error`→`done` double event | ✅ | ✅ | ◑ | ✅ | **Confirmed — HIGH** (fragile, not a guaranteed crash) |
| Token usage never persisted (breaks P6) | – | ✅ | ✅ | – | **Confirmed — HIGH** |
| `_persist` swallows failure → false success | ◑ | ✅ | ✅ | – | Confirmed — **HIGH** |
| History not token-budgeted (Decision 8) | ✅ | ✅ | ✅ | ✅ | Confirmed — MEDIUM |
| Full corpus through Redis payload | ✅ | ✅ | ✅ | ✅ | Confirmed — MEDIUM (demo-acceptable) |
| Injection collapsed to `declined_off_topic` | ✅ | ✅ | ✅ | ✅ | Confirmed — MEDIUM |
| `init_progress` races/clobbers worker state | ✅ | ✅ | – | – | Confirmed — MEDIUM |
| Escapable `<context>` delimiter | – | – | ✅ | – | Confirmed — MEDIUM |
| Guardrail fails **open** to ON_TOPIC | – | – | ✅ | ✅ | Confirmed — MEDIUM |
| `retrieved_ids` needs `CAST(... AS bigint[])` | ✅ | – | ◑ | ✅ | **FALSE POSITIVE** (live insert succeeded) |
| `asyncio.shield` on "unstarted coroutine" | – | – | – | ✅ | **FALSE POSITIVE** (`shield` does `ensure_future`) |

---

## False positives (validated and dismissed)

- **`retrieved_ids` requires an explicit `::bigint[]` cast (Alpha/Delta "High/Critical").** The live E2E inserted `retrieved_ids=[chunk_ids]` (a bare `list[int]`) with no cast and it **succeeded**, then `fetch_recent_turns` round-tripped (citations included). psycopg3 adapts `list[int] → bigint[]`. Not a bug. (An explicit cast would only matter for an *empty* list ambiguity — worth a one-line defensive add, but not the runtime failure claimed.)
- **"`yield` in `finally` crashes on every disconnect" (Beta/Delta Critical).** Empirically: with the real disconnect path (`request.is_disconnected()` returns `True`) the `done` yield is **skipped** → `aclose()` is clean, **no RuntimeError**. The pattern *does* raise `async generator ignored GeneratorExit` only if that yield is reached during `aclose()` — which the guard prevents on a genuine disconnect. So it's a real **fragility + contract** issue (HIGH), not a guaranteed crash. Gamma's analysis was correct.
- **`asyncio.shield` applied to an unstarted coroutine (Delta High).** `asyncio.shield()` calls `ensure_future()` internally, so the coroutine *is* scheduled. Not a defect.

---

## HIGH

### H1 — SSE terminal-event handling: `done` in `finally` + `error`→`done` double event
`apps/chat/abb_chat/routers/chat.py:76-89`. The `done` event is yielded inside `finally`; on the error path the generator emits `error` **and then** `done` (with `status=ERROR`, empty answer) — contradictory terminal signals a P5 client can mis-handle. And yielding in `finally` is fragile under `aclose()` (validated: crashes if the guard doesn't skip it). **Fix:** keep only `await asyncio.shield(_persist(...))` in `finally`; emit `done` from the `try` body on success only; error paths terminate with `error` alone.

### H2 — Token usage never captured or persisted (breaks P6)
`apps/chat/abb_chat/persistence.py:9-16`, `generation.py`. `chat_logs.prompt_tokens/completion_tokens` are never written, and generation never reads `usage_metadata`. P6's **already-defined** `PerformanceStats` needs `avg_total_tokens` + `estimated_cost_usd` — these will be permanently NULL, a silent downstream break. **Fix:** `ChatOpenAI(..., stream_usage=True)`, accumulate usage from the final stream chunk, add the two columns to `_INSERT`/`insert_chat_log`.

### H3 — Persistence failure is swallowed and reported as success
`apps/chat/abb_chat/routers/chat.py:101-115`. `_persist` catches all exceptions and returns `0`; the generator still emits a `done` with `chat_log_id=0`. Violates "fail loud" (CONVENTIONS §1.4) and the persist-every-turn requirement — the client sees success with no `chat_logs` row. **Fix:** on persist failure, emit a terminal `error` (or an explicit not-persisted state); never return a synthetic success id.

---

## MEDIUM

- **M1 — History not token-budgeted (Decision 8).** `context.py` budgets retrieved context, but `prompts.build_chat_messages` appends all (≤6) history turns untrimmed. Bounded for the demo, but a locked-decision deviation. **Fix:** budget `context + history`, trimming oldest turns; also skip/truncate a first chunk that alone exceeds the budget (`context.py:15`).
- **M2 — Full corpus through the Redis job payload** (`routers/ingest.py:17`). The entire `Corpus` JSON is enqueued (duplicated in Redis + API + worker memory). Fine for the demo corpus; doesn't scale. **Fix:** stage the corpus once (DB row / Redis key / object store), enqueue only a reference.
- **M3 — Injection indistinguishable in telemetry.** `guardrail` returns `INJECTION`, but the route maps every non-`ON_TOPIC` to `DECLINED_OFF_TOPIC`; `AnswerStatus`/`chat_logs` have no injection state. Security traffic can't be audited. **Fix:** add `AnswerStatus.DECLINED_INJECTION` (+ DB `CHECK`) and branch on the verdict.
- **M4 — Guardrail fails open.** `guardrail.classify` returns `ON_TOPIC` on any unrecognized LLM label. A bank safety classifier should **fail closed** (treat unknown as off-topic/declined). **Fix:** default to `OFF_TOPIC`.
- **M5 — Escapable context delimiter.** The grounding prompt wraps context in a literal `<context>…</context>`; scraped content (an untrusted attack surface per Decision 4) could embed `</context>` to "break out." The instruction layer is a second defense, so it's probabilistic, but it weakens a *required* control. **Fix:** per-request random sentinel delimiter and/or strip the delimiter token from chunk content.
- **M6 — Ingestion progress can regress.** `POST /ingest` enqueues **before** `init_progress`; a fast worker can set `RUNNING` and then `init_progress` overwrites it back to `QUEUED/0`. **Fix:** init progress before enqueue, or use `HSETNX`/non-clobbering writes.
- **M7 — Hybrid search degrades to dense-only for natural-language queries** *(audit gap — no reviewer caught)*. The live E2E logged `dense=40 sparse=0` for "How can I get a credit card from ABB?": `websearch_to_tsquery('simple', …)` ANDs every term **including stopwords** ("how/can/i/a/from"), so almost no chunk matches all → the sparse branch contributes nothing for conversational questions (it still helps for exact keyword/product-name queries). Retrieval survives on dense, but "hybrid" is half-dead for the chat use case. *(Lives in `libs/rag/retriever.py`.)* **Fix:** strip stopwords / use OR-of-terms or `plainto`/keyword extraction for the sparse branch while keeping the equal-language `simple` config.
- **M8 — Upstream error detail leaked to client.** `chat.py:71` forwards `ExternalServiceError.message` (which embeds raw OpenAI/SQL text) to the browser; same in each `AppError` handler. CONVENTIONS §5/§6 want safe messages. **Fix:** generic client `detail` per `code`, verbose detail server-side only.
- **M9 — Redis/arq failures not wrapped.** `routers/ingest.py` guards `enqueue_job() is None` but doesn't wrap Redis exceptions (enqueue/status) in `ExternalServiceError` — inconsistent with the chat path. **Fix:** wrap them.
- **M10 — Test gaps on the hardest paths.** No tests for real async-cancel disconnect, persist-failure semantics, the progress init/worker race, or `rewrite_query`/`stream_answer`. (Persistence binding is now validated by the E2E.) **Fix:** add them.

---

## LOW

- **L1** Token budget uses `cl100k_base`; gpt-4o uses `o200k_base` — count is an estimate (`chunking.count_tokens`).
- **L2** Citations can include sources whose chunk was trimmed out of the packed context (`context.py`).
- **L3** `Verdict` enum values are lowercase (internal enum) vs SCREAMING_SNAKE (`guardrail.py`).
- **L4** `memory.py` comment says "Last 3 Q/A pairs" but the limit is 6.
- **L5** No fail-fast config validation; an empty `OPENAI_API_KEY` only fails on first call (CONVENTIONS §5).
- **L6** Flat module layout vs CONVENTIONS §2 stereotype dirs (`services/`, `repositories/`, `api/routers/`).
- **L7** `# type: ignore[misc]` in `progress.py` + `Any` via `request.app.state.redis` (redis-py union typing — acceptable).
- **L8** Worker image carries `torch`/`sentence-transformers` though the worker only embeds (no rerank) — image weight.
- **L9** `GET /sessions/{id}` exposes full history with no access control (auth out of scope per master plan §8a).
- **L10** Prompts are raw message builders, not LangChain `ChatPromptTemplate` (plan named `ChatPromptTemplate`); behavior equivalent.

## Conventions compliance (`CONVENTIONS.md`)

| Area | Status | Note |
| --- | :-: | --- |
| Fail loud (§1.4) | ❌ | H3 (`_persist` swallows failure) |
| Typed boundary errors (§5) | ⚠️ | OpenAI paths wrapped; Redis/arq not (M9); client detail leak (M8) |
| Async / no CPU on loop (§7) | ✅ | rerank offloaded; all I/O async |
| No `Any` (§1.7) | ✅ (with `# type: ignore[misc]` for redis-py) |
| SQL parameterized | ✅ | chat_logs insert/select bound |
| ruff/mypy strict (§10,§12) | ✅ | green |
| Tests prove behavior (§8) | ⚠️ | happy paths solid; M10 gaps; analytics stub untested |
| Security | ⚠️ | injection-defended + SecretStr + CORS; M4 fail-open, M5 delimiter, M8 leak |

## Remediation order
1. **H1, H2, H3** before P5/P6 lean on chat output/analytics: fix SSE terminal events, persist token usage, fail loud on persist error.
2. **M3, M4, M5, M6, M8, M9** (security + correctness, cheap): injection status, fail-closed guardrail, nonce delimiter, progress-before-enqueue, generic error detail, wrap Redis errors.
3. **M1, M2, M7** (budget history; stage corpus; fix sparse for NL queries — `libs/rag`).
4. **M10 + Low**: tests + polish.
