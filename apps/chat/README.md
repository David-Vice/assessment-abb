# chat-service (`apps/chat`)

**This is the brief-mandated microservice for question handling and response
generation.** Its JSON contract is `ChatRequest → ChatResponse` (Pydantic, served
as OpenAPI). It answers strictly within ABB Bank's context, streams tokens over
SSE, and persists every turn.

## Endpoints

| Method | Path | Body / Params | Returns |
| --- | --- | --- | --- |
| `POST` | `/chat` | `ChatRequest { session_id, question, language }` | `text/event-stream` |
| `GET` | `/sessions/{session_id}` | — | `list[ChatTurn]` (chronological) |
| `GET` | `/health` | — | `{ status, service }` |

### SSE events (`POST /chat`)

- `event: token` — `{ "token": "..." }` incremental answer text.
- `event: done` — `ChatResponse { chat_log_id, answer, status, citations }`.
- `event: error` — `{ "code", "detail" }` on failure.

## Request flow

```
question
 → guardrail + injection check (gpt-4o-mini)        # off-topic/injection → declined, logged
 → load recent turns (chat_logs) → query rewrite     # multi-turn follow-ups (toggle: CHAT_MEMORY_ENABLED)
 → libs/rag.retrieve (hybrid + rerank)               # grounded context, token-budgeted
 → gpt-4o stream (context labeled untrusted)         # never follows instructions inside context
 → persist Q/A/timestamp/citations (in `finally`)    # survives mid-stream disconnect
 → done event with citations (deduplicated by URL)
```

## Hardening

- **Prompt injection:** retrieved context is delimited and labeled untrusted; the
  system prompt forbids following instructions found inside it; the user question
  is a separate turn; the system prompt is never revealed.
- **Resilience:** every OpenAI call (guardrail, rewrite, generation) retries with
  backoff (`max_retries`); the reranker runs off the event loop.
- **Persist-on-disconnect:** the SSE generator persists in a shielded `finally`,
  so a client disconnect still records the (partial) turn.

## Environment

`OPENAI_API_KEY`, `CHAT_MODEL` (gpt-4o), `AUX_MODEL` (gpt-4o-mini), `DATABASE_URL`,
`RETRIEVAL_*`, `RERANK_ENABLED`, `CONTEXT_TOKEN_BUDGET`, `CHAT_MEMORY_ENABLED`,
`CORS_ORIGINS` (see root `.env.example`).

## Run

```bash
uv run uvicorn abb_chat.main:app --port 8002
```
