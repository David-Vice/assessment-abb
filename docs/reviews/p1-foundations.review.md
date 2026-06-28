# Multi-Perspective Review — P1 Foundations

**Target:** entire P1 foundation scaffold (no git history; whole tree reviewed as new code)
**Reviewers:** Alpha (opus-max), Beta (gpt-5.4), Gamma (composer-2), Delta (sonnet-medium)
**Audit:** main agent, cross-validated against actual code + empirical checks

---

## Verdict

The architecture, contracts, layering, and conventions are sound. But the scaffold **does not yet pass its own Day-2 de-risking gate** (`docker compose up` green): **two confirmed CRITICAL blockers** break DB init and image builds. One widely-flagged "critical" (React/TSX) is a **false positive** — `pnpm type-check` passes. Fix the two criticals + the highs and the foundation is solid.

| Severity | Count (confirmed) |
| -------- | ----------------- |
| Critical | 2 |
| High | 2 |
| Medium | 6 |
| Low | 7 |
| False positives rejected | 4 |

---

## Confirmed findings

### CRITICAL

**C1 — `unaccent()` in a STORED generated column is not IMMUTABLE → DB init crashes**
`infra/postgres/init.sql` (chunks.tsv). Flagged by Alpha, Gamma, Delta; externally validated against PostgreSQL docs; consistent with known `unaccent` STABLE classification. Postgres rejects `GENERATED ALWAYS AS (... unaccent(content)) STORED` with *"generation expression is not immutable"*, so `init.sql` aborts on first boot and every service waiting on a healthy Postgres is blocked.
*Fix:* add an IMMUTABLE wrapper and use it in the generated column:
```sql
CREATE OR REPLACE FUNCTION immutable_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS $$ SELECT unaccent('unaccent', $1) $$;
-- tsv ... GENERATED ALWAYS AS (to_tsvector('simple', immutable_unaccent(content))) STORED
```

**C2 — Backend Dockerfiles copy only 3 of 6 uv workspace members → `uv sync --frozen` fails**
`apps/{ingestion,chat,analytics}/Dockerfile`. Flagged by Gamma; externally validated against uv workspace behavior. The root `pyproject.toml` lists six members; uv resolves the whole workspace before syncing, so the missing members' `pyproject.toml` files cause `uv sync --frozen` to error → all three image builds fail.
*Fix:* copy **every** member's `pyproject.toml` before the targeted sync (only the target + `contracts`/`rag` need source):
```dockerfile
COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/
COPY libs/rag/pyproject.toml libs/rag/
COPY apps/ingestion/pyproject.toml apps/ingestion/
COPY apps/chat/pyproject.toml apps/chat/
COPY apps/analytics/pyproject.toml apps/analytics/
COPY apps/scraper/pyproject.toml apps/scraper/
```

### HIGH

**H1 — CI workflow is undiscoverable by GitHub Actions**
`infra/ci/ci.yml`. Flagged by Beta; externally validated. GitHub only runs workflows under `.github/workflows/`. As-is, no gate runs on push/PR.
*Fix:* add `.github/workflows/ci.yml` (can be the same file moved, or a thin caller).

**H2 — `openai_api_key` empty default, no fail-fast, plain `str`**
`libs/rag/abb_rag/settings.py`. Flagged by Alpha, Beta, Delta. Should be `SecretStr` (prevents leakage in logs/tracebacks) and validated where used (P3), so a missing key fails clearly instead of producing cryptic 401s.
*Fix:* `openai_api_key: SecretStr = SecretStr("")`; assert non-empty in the LLM/embeddings client (P3). Hard fail-fast at P1 is intentionally avoided so health endpoints boot without a real key.

### MEDIUM

| # | Finding | Location | Fix |
| - | ------- | -------- | --- |
| M1 | CI uses `uv sync --all-packages` (not `--locked`) while Docker uses `--frozen` → lock drift passes CI, fails Docker | `infra/ci/ci.yml` | add `--locked` in CI (Gamma, Delta) |
| M2 | `uv run` as non-root over root-owned `.venv` may attempt a write-sync at boot | `apps/*/Dockerfile` CMD | `uv run --no-sync` (or `ENV UV_FROZEN=1`) + `chown -R appuser /app` (Gamma) |
| M3 | No `CHECK` constraints mirroring enums (`language`, `segment`, `status`) | `infra/postgres/init.sql` | add `CHECK (... IN (...))` (Beta, Delta) |
| M4 | `chunks` has no `UNIQUE (document_id, ordinal)` → no clean upsert key for P3 | `infra/postgres/init.sql` | add the unique constraint (Beta, Delta) |
| M5 | `DistributionStats` uses `dict[str, int]`, erasing enum typing at a published boundary | `packages/contracts/abb_contracts/analytics.py` | `dict[Language, int]` / `dict[Segment, int]` (Beta, Gamma) |
| M6 | pytest `testpaths` includes `apps/web` → can crawl `node_modules` | `pyproject.toml` | add `norecursedirs = ["node_modules", ".venv", "apps/web"]` (Gamma) |

### LOW

| # | Finding | Location | Fix |
| - | ------- | -------- | --- |
| L1 | `uv:latest` not pinned | `apps/*/Dockerfile` | pin a uv version/digest (Beta) |
| L2 | Scraper CLI raises raw `NotImplementedError` (traceback) | `apps/scraper/abb_scraper/cli.py` | clean `raise SystemExit("scraper lands in P2")` (Beta) |
| L3 | `ValidationError` shadows `pydantic.ValidationError` | `libs/rag/abb_rag/exceptions.py` | rename `InputValidationError` (Alpha, Gamma, Delta) |
| L4 | Enum **values** are lowercase, deviating from CONVENTIONS §8 | `packages/contracts/abb_contracts/enums.py` | **justified** (ISO codes / DB text) — document the exception in `CONVENTIONS.md` rather than change values (all four; resolved by doc) |
| L5 | `url` fields are unvalidated `str` | `corpus.py`, `chat.py` | optional `HttpUrl`/pattern; low priority (Alpha, Gamma) |
| L6 | `get_logger` casts to `BoundLogger` but configured logger is `FilteringBoundLogger` | `libs/rag/abb_rag/log.py` | annotate `FilteringBoundLogger`, drop the cast (Gamma) |
| L7 | No `py.typed` markers | `packages/contracts`, `libs/rag` | add `py.typed` for installed-consumer typing (Gamma) |

### Deferred by prior user decision
- **CORS `allow_methods/headers=["*"]`** (Delta): CORS hardening was explicitly de-scoped earlier. Origins are already env-locked. Revisit if/when scope changes.

---

## False positives (rejected with evidence)

| Claim | Source | Why rejected |
| ----- | ------ | ------------ |
| C3: `App(): React.JSX.Element` → TS2686, breaks build/CI | Gamma | **`pnpm type-check` passes (exit 0)** — `@types/react@19` exposes `React` as a UMD namespace usable without import. Empirically refuted. |
| Missing `__init__.py` in app packages | Alpha (M3, hedged) | Files exist (`apps/*/abb_*/__init__.py`). |
| Web Dockerfile COPY path wrong | Alpha (M1) | Self-retracted; multi-stage has build-context access. Valid as-is. |
| `.env` `*_URL=localhost` wrong for containers | Alpha (L4) | Correct — these are browser→host URLs for the SPA; published ports map to localhost. |

---

## Gaps found in audit (no reviewer caught)

- **Temp review artifact**: `.review-scope.md` was created for the reviewers and has been removed (was not gitignored).
- **pgvector version dependency**: `HALFVEC` requires pgvector ≥ 0.7.0; `pgvector/pgvector:pg16` (current) satisfies this, but the dependency should be noted so the image tag isn't downgraded.
- **`web` service has no healthcheck** (Alpha L3 partially) — `docker compose up --wait` won't gate on the frontend; minor.

---

## Cross-model signal

- **Strong consensus (3–4 models):** C1 (DB immutability), H2 (api key), L3 (`ValidationError` shadow), L4 (enum convention).
- **High-value unique finds:** C2 (Gamma — Docker workspace members), H1 (Beta — CI discovery path), M6 (Gamma — pytest node_modules). These are exactly the cross-model diversity wins: each is a real blocker/issue only one model surfaced.
- **Divergence resolved by running the code:** C3 — Gamma confident it breaks; empirical `tsc` proves otherwise.

## Recommended fix order
1. **C1, C2** (unblock the Day-2 gate).
2. **H1, H2.**
3. **M1–M6** (cheap foundation hardening that pays off in P3/P4).
4. **L1–L7** (polish; L4 is a one-line CONVENTIONS note).
