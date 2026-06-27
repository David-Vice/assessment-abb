---
phase: P6
title: Visualization — Analytics Service + recharts Dashboard
depends_on: [P4]
enables: []
---

# P6 — Visualization

Turn stored interactions into insight. The analytics-service aggregates
`chat_logs`; the frontend renders an interactive dashboard with
recharts. Satisfies brief requirement 3 (charting library over stored Q&A).

## Decisions

1. **Aggregation in the analytics-service, not the browser**
   - Decision: SQL aggregations behind read-only JSON endpoints; frontend only renders.
   - Rationale: Efficiency (scored); keeps heavy queries server-side; browser stays light.

2. **recharts for charts**
   - Decision: recharts (matches `timeback-frontend`); responsive containers.
   - Rationale: Decision 2; consistent, declarative, themeable.

3. **Insight set tied to the brief + chosen features**
   - Decision: Ship a focused, meaningful panel rather than vanity charts:
     - **Question volume over time** (line/area; group by hour/day).
     - **Top questions / themes** (bar; top-N by frequency, normalized).
     - **Latency & token/cost** (avg/p95 latency; tokens per answer → est. cost).
     - **Off-topic / unanswered rate** (guardrail declines vs answered).
     - **Language & segment mix** (pie/stacked — AZ/EN/RU, individuals/business/about).
   - Rationale: Directly visualizes "insights into user interactions" and showcases the system's quality signals.

4. **Time-range + language filters**
   - Decision: Dashboard filters (range, language) flow to query params.
   - Rationale: Interactive exploration; reuses the same aggregation endpoints.

## Plan

### analytics-service endpoints (JSON)
- `GET /analytics/volume?from&to&bucket` → time series of question counts.
- `GET /analytics/top-questions?from&to&limit` → frequency-ranked questions.
- `GET /analytics/performance?from&to` → avg/p95 latency, avg tokens, est. cost.
- `GET /analytics/quality?from&to` → answered vs off-topic/declined.
- `GET /analytics/distribution?from&to` → language + segment breakdown.
- `GET /analytics/summary?from&to` → headline KPI cards (totals, avg latency, answered rate).

All DTOs in `packages/contracts`; typed into the frontend via OpenAPI.

### Frontend dashboard module
```
apps/web/src/modules/dashboard/
├── components/ (kpi-cards, volume-chart, top-questions,
│                performance-chart, quality-chart, distribution-chart)
├── hooks/ (use-analytics queries via TanStack Query)
└── screens/dashboard.screen.tsx
```

## Breakdown

- **analytics-service**: SQL aggregation queries (time-bucketing via `date_trunc`, top-N, percentile via `percentile_cont`), DTOs, endpoints, caching of expensive queries in Redis (short TTL).
- **Frontend**: dashboard screen, KPI cards, five recharts charts, range + language filters, loading skeletons, empty states.
- **Tests**: analytics query unit tests against seeded fixtures (counts, percentiles correct); chart components render with mock data.
- **Docs**: analytics endpoints in service README; dashboard usage in web README.
- **Verification**: after running several chat questions (incl. off-topic), dashboard shows non-trivial, correct values across all panels; filters update charts; numbers reconcile with raw `chat_logs`.
