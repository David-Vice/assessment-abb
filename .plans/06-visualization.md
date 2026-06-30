---
phase: P6
title: Visualization — Analytics Endpoints + recharts Dashboard
depends_on: [P4, P5]
enables: [P8]
---

# P6 — Visualization

Turn every persisted `chat_logs` row into actionable insight. The analytics
service adds six SQL-aggregation endpoints; the frontend gains a full dashboard
screen built with recharts inside the module structure established by P5.

Satisfies brief requirement **3** (charting library over stored Q&A interactions).

---

## What already exists (no re-work)

| Item | Where |
| ---- | ----- |
| All 6 DTO contracts (`VolumeSeries`, `TopQuestion`, `PerformanceStats`, `QualityStats`, `DistributionStats`, `AnalyticsSummary`) | `packages/contracts/abb_contracts/analytics.py` |
| Analytics FastAPI shell with CORS + error handler + `/health` | `apps/analytics/abb_analytics/main.py` |
| `apiFetchAnalytics(path)` helper | `apps/web/src/lib/api.ts` |
| Vite dev proxy routing `/analytics` → `localhost:8003` | `apps/web/vite.config.ts` |
| `recharts` installed | `apps/web/package.json` |
| TanStack Query + module layout pattern | P5 convention |
| Hand-written Zod schemas at API boundary | P5 convention (no orval) |

**`QualityStats` contract gap to fix first:** the model has `answered`,
`declined_off_topic`, and `error` but is missing `declined_injection` — the
`chat_logs.status` CHECK has it and the frontend would silently undercount
declines. Add it before building the endpoint.

---

## Decisions

1. **Aggregation server-side, rendering client-side**
   Decision: SQL aggregations (`date_trunc`, `percentile_cont`, `COUNT ... GROUP BY`)
   behind read-only JSON endpoints. The browser only renders.
   Rationale: Efficiency criterion; keeps heavy work off the client; single source of truth.

2. **recharts with responsive containers**
   Decision: `ResponsiveContainer` wrapping every chart; dark-mode aware via
   Tailwind CSS vars inherited from P5's `index.css`.
   Rationale: Already installed; matches `timeback-frontend` stack; declarative and themeable.

3. **Four focused charts + KPI cards**
   Decision: ship meaningful insight panels only:
   - **KPI summary bar** — total questions, answered rate, avg latency, p95 latency,
     avg tokens, est. cost (latency/token/cost KPIs scoped to `status='answered'` —
     guardrail declines short-circuit before generation and would dilute them).
   - **Volume over time** — AreaChart grouped by hour (last 24 h) or day (last 30 d),
     zero-filled client-side so empty buckets dip to zero instead of interpolating.
   - **Answer quality** — PieChart of answered / declined_off_topic / declined_injection / error.
   - **Language & segment mix** — two BarCharts (AZ/EN/RU counts; individuals/business/about/other).
     Segment mix counts *citations* (a multi-source answer counts once per source),
     not questions, so it's labeled "Citations by segment."
   - **Top questions** — horizontal BarChart of top-10 questions by frequency.
   Rationale: Directly visualizes "insights into user interactions" with real quality signals.
   A fifth panel (avg/p95 latency as a time series) was scoped out: `PerformanceStats`
   is a flat aggregate by design, and a bucketed latency series would be a new query
   + new chart for marginal value over the KPI cards already shown above.

4. **Time-range + language filter**
   Decision: `from` / `to` ISO date params + optional `lang` query param flow to
   every endpoint; TanStack Query re-fetches when filters change.
   Rationale: Interactive exploration; same endpoints handle all filter combinations.

5. **Short Redis cache on every aggregation endpoint**
   Decision: 60-second TTL on all six `/analytics/*` endpoints (the cache helper
   generalizes over any `TypeAdapter`-serializable type, including bare lists like
   `list[TopQuestion]`, so there's no reason to special-case which endpoints get it).
   The cache key truncates `from`/`to` to the minute — the client recomputes them
   fresh (`new Date()`) on every page load, so millisecond precision would make
   the TTL effectively never hit.
   Rationale: Redis is already connected; prevents repeated identical aggregations on
   a busy demo session without stale data risk.

6. **Zod schemas hand-written from contracts (no orval)**
   Decision: consistent with P5 — no codegen; add analytics schemas to `lib/schemas.ts`.
   Rationale: P5 established this pattern; orval adds tooling complexity for no gain on a small surface.

---

## Plan

### 1. Fix `QualityStats` contract

`packages/contracts/abb_contracts/analytics.py`:
```python
class QualityStats(BaseModel):
    answered: int
    declined_off_topic: int
    declined_injection: int   # add
    error: int
```

### 2. Analytics-service endpoints

New file `apps/analytics/abb_analytics/routers/analytics.py`:

| Method | Path | Returns | Notes |
|--------|------|---------|-------|
| GET | `/analytics/summary` | `AnalyticsSummary` | Total Q, answered rate, avg latency |
| GET | `/analytics/volume` | `VolumeSeries` | `date_trunc(:bucket)` time series |
| GET | `/analytics/top-questions` | `list[TopQuestion]` | `COUNT GROUP BY question ORDER BY DESC LIMIT :n` |
| GET | `/analytics/performance` | `PerformanceStats` | `AVG`, `percentile_cont(0.95)`, token sums, cost calc |
| GET | `/analytics/quality` | `QualityStats` | `COUNT ... GROUP BY status` |
| GET | `/analytics/distribution` | `DistributionStats` | `COUNT ... GROUP BY language`, `GROUP BY segment` |

All accept `?from=ISO&to=ISO`; volume also accepts `?bucket=hour|day` (a
`Literal["hour", "day"]` FastAPI param — invalid values 422 automatically).
Cache every endpoint's response in Redis at 60-second TTL.
Wire router into `main.py`.

### 3. Frontend analytics Zod schemas

Add to `apps/web/src/lib/schemas.ts`:
`TimeBucketSchema`, `VolumeSeriesSchema`, `TopQuestionSchema`,
`PerformanceStatsSchema`, `QualityStatsSchema`, `DistributionStatsSchema`,
`AnalyticsSummarySchema` — mirroring the contracts exactly.

### 4. Frontend dashboard module

```
apps/web/src/modules/dashboard/
├── hooks/
│   └── use-analytics.ts        # TanStack Query per endpoint; dateRange + lang state
├── lib/
│   └── fill-buckets.ts         # zero-fills empty volume buckets client-side
├── components/
│   ├── kpi-cards.tsx            # 6 summary cards (total, answered%, latencies, tokens, cost)
│   ├── volume-chart.tsx         # AreaChart — questions over time
│   ├── quality-chart.tsx        # PieChart — answer/decline/error breakdown
│   ├── distribution-chart.tsx   # two BarCharts — language mix + citations-by-segment mix
│   ├── top-questions-chart.tsx  # horizontal BarChart — top 10 questions
│   ├── chart-card.tsx           # shared card chrome (title, empty state, palette)
│   └── date-range-filter.tsx    # preset range buttons + lang selector
└── dashboard.screen.tsx         # composes all; loading placeholders; empty/error state
```

### 5. Wire into App.tsx

Add `'dashboard'` as a third `corpusStatus`-independent screen.
Add a nav item in `Header` (reuse existing nav i18n keys).
Route: show dashboard button once corpus is `'ready'`; always accessible via header.

### 6. i18n additions

Add `dashboard.*` keys to `en.ts`, `az.ts`, `ru.ts` (panel titles, filter labels,
empty state text, loading text).

---

## Breakdown

- **Backend**: `analytics.py` router (6 SQL queries), `QualityStats` fix, Redis cache helper (generic `TypeAdapter`-based, covers all 6 endpoints), wired into `main.py`. Performance KPIs scoped to `status = 'answered'`. DB errors never reach clients raw (generic `_PUBLIC_DETAIL` mapping + server-side `logger.error`, same pattern as the chat service). Unit tests: seeded fixture rows → assert counts/percentiles correct; DB-backed integration tests (seeded `chat_logs` rows against real Postgres, skipped if unreachable) cover the actual SQL (`date_trunc`, `percentile_cont`, `jsonb_array_elements`); a router test covers the `bucket` 422 validation.
- **Frontend**: `use-analytics.ts` hook, `fill-buckets.ts` util (zero-fills sparse volume series, unit-tested), 5 components, `dashboard.screen.tsx`, i18n keys, filter state. KPI cards show a pulse placeholder while loading instead of fake zeros. Volume chart axis labels use UTC getters to match the UTC buckets from Postgres.
- **Verification**: run ≥10 chat questions (mix of answered, off-topic, injection, multi-language) → dashboard shows correct totals across all panels; language filter updates charts; `docker compose up` still green.
