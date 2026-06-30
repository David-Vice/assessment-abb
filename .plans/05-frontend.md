---
phase: P5
title: Frontend — Upload, Streaming Chat, Citations, i18n (AZ/RU/EN)
depends_on: [P4]
enables: [P6]
---

# P5 — Frontend (Vite React SPA)

The user-facing app: upload the corpus to browser storage, ingest it, then chat
with grounded, cited, streamed answers in AZ/RU/EN (all first-class). Satisfies
brief requirements 2a (localStorage upload) and 2c (conversational interface),
plus Design.

## Decisions

1. **Vite + React 19 + TS, mirroring `timeback-frontend`**
   - Decision: Tailwind + shadcn/ui (Radix), TanStack Query for server state, light client state (Zustand or RTK — Zustand default for app size), react-markdown + DOMPurify for answer rendering.
   - Rationale: Decision 2; idiomatic, polished, fast.

0. **Design is a first-class deliverable (not an afterthought)**
   - Decision: A deliberate UX pass is scoped into this phase — not left to the end. Defined flows (empty → uploading → indexing → ready → chatting → error), a coherent ABB-appropriate visual identity (palette, spacing, typography), responsive layout, dark mode, accessible components (keyboard + aria), skeleton/loading/error states for every async action, and an obvious primary "Ask ABB a question" path.
   - Rationale: "Design" is an explicit scored criterion. Foregrounding it (vs polishing at P8) is what separates a demo that feels finished from one that feels rushed.

2. **Corpus stored in localforage (IndexedDB), not raw localStorage**
   - Decision: Persist uploaded corpus + metadata via `localforage`; the term "local storage" in the brief is honored (localforage uses the browser's local storage layer) while avoiding the ~5MB `localStorage` cap.
   - Rationale: A full corpus exceeds `localStorage` limits; IndexedDB is the correct browser-local store. Chat is gated on "corpus present".

3. **Upload triggers ingestion + progress UI**
   - Decision: On upload, save to localforage AND `POST /ingest`; poll `GET /ingest/{job_id}` with TanStack Query; show a progress bar; enable chat only when indexing completes.
   - Rationale: Connects the literal localStorage requirement to real server-side indexing (resolves the brief's localStorage-vs-vectorDB tension cleanly).

4. **SSE streaming chat with incremental render + citations panel**
   - Decision: `@microsoft/fetch-event-source` POSTs to `/chat`; tokens render live; the final event populates a citations list (clickable deep links to ABB pages).
   - Rationale: Decision 2a; trust + "answered in ABB context" made visible.

5. **i18n via i18next — AZ / RU / EN all first-class**
   - Decision: All three languages get complete UI string coverage (no partial language). Selected language drives both the interface and the `language` field sent to chat/retrieval; answers return in the chosen language.
   - Rationale: Decision 8 + the equal-support requirement; ABB's primary language is Azerbaijani, so AZ must be as complete as EN/RU.

6. **Generated Zod schemas from OpenAPI + runtime validation at the boundary**
   - Decision: `orval` (or `openapi-zod-client`) generates **Zod schemas** from the aggregated backend OpenAPI. Every backend response is `.parse()`d at the API boundary; TS types are derived via `z.infer`. The `corpus.json` upload reuses the same Zod system.
   - Rationale: Decision 2b. Production-grade: compile-time safety **and** runtime validation, auto-synced from the backend (no manual drift). A backend change you forget to regenerate fails loudly at the exact boundary rather than silently lying through stale types. Treats the network as untrusted even though we own both ends.

## Plan

### Screens / flow
1. **Onboarding / Upload** — drop `corpus.json` → validate shape (zod mirror of `Corpus`) → save to localforage → start ingestion → progress.
2. **Chat** — message list (markdown), streaming assistant bubble, citations panel per answer, language switcher, suggested questions.
3. **Dashboard** — link to analytics (built in P6).

### State & data
- `useCorpus` (localforage read/write + "is uploaded" gate).
- `useIngestion` (TanStack Query mutation + polling).
- `useChat` (SSE stream handling, message store, session_id in localforage).

### Module layout (mirrors timeback-frontend conventions)
```
apps/web/src/modules/
├── common/ (ui/shadcn, hooks, utils, i18n, api-client)
├── upload/ (components, hooks, screens)
├── chat/   (components, hooks, screens, models)
└── dashboard/ (P6)
```

## Implementation notes (added during P5)

- **Zod schemas**: hand-written in `src/lib/schemas.ts` directly from `packages/contracts` Pydantic models. No `orval` run-time generation step — contracts are small, stable, and we own both ends. TS types derived via `z.infer`.
- **SSE reader**: custom `fetch()` + `ReadableStream` parser in `use-chat.ts`. No `@microsoft/fetch-event-source` dependency — avoids package complexity while handling all event types (token/done/error) and abort correctly.
- **No React Router**: state-machine rendering (Zustand `corpusStatus`) drives screen selection instead of URL routing. Reduces complexity for a single-view demo. Upload → Ingesting → Chat states are all handled via conditional renders in `App.tsx`.
- **recharts** installed now for use in P6.
- **Dark mode**: Tailwind `darkMode: 'class'` toggled via Zustand `theme` written to `document.documentElement`.
- **Persisted state**: Zustand `persist` middleware stores `language`, `theme`, `corpusStatus`, `jobId`, `sessionId` in `localStorage`. `corpus` object (large) stored in `localforage` (IndexedDB).

## Breakdown

- **Scaffold**: finalize Vite + Tailwind + shadcn setup from P1; routing (react-router); i18next with `en`/`az`/`ru` resource files.
- **API client**: OpenAPI → Zod schema generation script (`orval`/`openapi-zod-client`); `apiFetch` wrapper that `.parse()`s every response at the boundary (typed errors on validation failure); SSE helper.
- **Upload module**: dropzone, client-side schema validation, localforage persistence, ingestion trigger + progress bar, error states.
- **Chat module**: streaming hook, message components (user/assistant/markdown via DOMPurify), citations panel (deep links + segment/lang badges), language switcher, suggested questions, empty/loading/error states, off-topic refusal rendering.
- **Design pass**: responsive, dark mode, ABB-appropriate palette, skeleton loaders, accessible (keyboard, aria).
- **Tests**: Vitest + Testing Library for upload validation (Zod), chat reducer/stream handling; mock SSE.
- **Docs**: `apps/web/README.md` — run, env (API base URLs), build.
- **Verification**: upload sample corpus → progress → chat streams a cited answer → switch language (AZ/RU/EN each complete) → answer in that language; refresh keeps corpus (localforage) + session.
