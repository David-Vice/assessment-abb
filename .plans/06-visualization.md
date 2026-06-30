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

3. **Five focused charts + KPI cards**
   Decision: ship meaningful insight panels only:
   - **KPI summary bar** — total questions, answered rate, avg latency, est. cost.
   - **Volume over time** — AreaChart grouped by hour (last 24 h) or day (last 30 d).
   - **Answer quality** — PieChart of answered / declined_off_topic / declined_injection / error.
   - **Language & segment mix** — two BarCharts (AZ/EN/RU counts; individuals/business/about/other).
   - **Top questions** — horizontal BarChart of top-10 questions by frequency.
   - **Latency & cost** — LineChart of avg/p95 latency over time + token totals.
   Rationale: Directly visualizes "insights into user interactions" with real quality signals.

4. **Time-range + language filter**
   Decision: `from` / `to` ISO date params + optional `lang` query param flow to
   every endpoint; TanStack Query re-fetches when filters change.
   Rationale: Interactive exploration; same endpoints handle all filter combinations.

5. **Short Redis cache on expensive endpoints**
   Decision: 60-second TTL on `/analytics/volume`, `/analytics/performance`, and
   `/analytics/summary` (the three with `percentile_cont` or full-table scans).
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

All accept `?from=ISO&to=ISO`; volume also accepts `?bucket=hour|day`.
Cache summary / volume / performance responses in Redis at 60-second TTL.
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
├── components/
│   ├── kpi-cards.tsx            # 4 summary cards (total, answered%, avg latency, cost)
│   ├── volume-chart.tsx         # AreaChart — questions over time
│   ├── quality-chart.tsx        # PieChart — answer/decline/error breakdown
│   ├── distribution-chart.tsx   # two BarCharts — language mix + segment mix
│   ├── top-questions-chart.tsx  # horizontal BarChart — top 10 questions
│   ├── performance-chart.tsx    # LineChart — latency + token trends
│   └── date-range-filter.tsx    # from/to pickers + lang selector
└── dashboard.screen.tsx         # composes all; loading skeletons; empty state
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

- **Backend**: `analytics.py` router (6 SQL queries), `QualityStats` fix, Redis cache helper, wired into `main.py`. Unit tests: seeded fixture rows → assert counts/percentiles correct.
- **Frontend**: `use-analytics.ts` hook, 6 components, `dashboard.screen.tsx`, i18n keys, filter state. Component tests: mock API data → assert chart renders non-trivially.
- **Verification**: run ≥10 chat questions (mix of answered, off-topic, injection, multi-language) → dashboard shows correct totals across all panels; language filter updates charts; `docker compose up` still green.
