import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from abb_contracts import AnswerStatus, ChatRequest, ChatResponse, ChatTurn, Citation, Language
from abb_rag import AppError, get_logger, get_settings, retrieve, session_scope
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from abb_chat.context import build_context, to_citations
from abb_chat.generation import TokenUsage, stream_answer
from abb_chat.guardrail import Verdict, classify
from abb_chat.lang_detect import auto_language
from abb_chat.memory import load_history, rewrite_query
from abb_chat.persistence import fetch_recent_turns, insert_chat_log
from abb_chat.prompts import off_topic_refusal

logger = get_logger(__name__)
router = APIRouter(tags=["chat"])

SSE_PING_SECONDS = 15
SESSION_HISTORY_LIMIT = 50

_DECLINED_STATUS = {
    Verdict.OFF_TOPIC: AnswerStatus.DECLINED_OFF_TOPIC,
    Verdict.INJECTION: AnswerStatus.DECLINED_INJECTION,
}

# Safe, generic client-facing messages — raw upstream/SQL detail stays in logs.
_PUBLIC_DETAIL = {
    "UPSTREAM_ERROR": "A required service is temporarily unavailable. Please try again.",
    "VALIDATION_ERROR": "The request was invalid.",
    "NOT_FOUND": "The requested resource was not found.",
    "PERSIST_FAILED": "The answer could not be saved. Please try again.",
    "INTERNAL_ERROR": "An unexpected error occurred. Please try again.",
}


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> EventSourceResponse:
    return EventSourceResponse(_chat_events(request, body), ping=SSE_PING_SECONDS)


@router.get("/sessions/{session_id}", response_model=list[ChatTurn])
async def get_session(session_id: UUID) -> list[ChatTurn]:
    return await fetch_recent_turns(session_id, SESSION_HISTORY_LIMIT)


async def _chat_events(request: Request, body: ChatRequest) -> AsyncIterator[dict[str, str]]:
    settings = get_settings()
    started = time.monotonic()
    answer_parts: list[str] = []
    citations: list[Citation] = []
    retrieved_ids: list[int] = []
    usage = TokenUsage()
    status = AnswerStatus.ANSWERED
    persisted = False

    # Detect language from the question text; fall back to the UI-selected language
    # when the question is too short or ambiguous. This runs once per request so
    # each question responds in its own language independently.
    effective_language = auto_language(body.question, hint=body.language)

    try:
        verdict = await classify(body.question)
        if verdict is not Verdict.ON_TOPIC:
            status = _DECLINED_STATUS[verdict]
            refusal = off_topic_refusal(effective_language)
            answer_parts.append(refusal)
            logger.info(
                "chat_declined",
                verdict=verdict.value,
                language=effective_language.value,
                ui_language=body.language.value,
            )
            yield _event("token", {"token": refusal})
        else:
            history = await load_history(body.session_id) if settings.chat_memory_enabled else []
            search_query = await rewrite_query(body.question, history) if history else body.question
            async with session_scope() as session:
                chunks = await retrieve(session, search_query, effective_language)
            retrieved_ids = [chunk.chunk_id for chunk in chunks]
            citations = to_citations(chunks)
            context = build_context(chunks, settings.context_token_budget)

            async for token in stream_answer(
                body.question, effective_language, context, history, usage
            ):
                if await request.is_disconnected():
                    break
                answer_parts.append(token)
                yield _event("token", {"token": token})

        # Success path: persist, then emit the single terminal `done` event.
        # Skipped if the client already left — the `finally` still persists.
        if not await request.is_disconnected():
            chat_log_id = await asyncio.shield(
                _persist(
                    body,
                    effective_language,
                    answer_parts,
                    status,
                    citations,
                    retrieved_ids,
                    usage,
                    started,
                    settings.chat_model,
                )
            )
            persisted = True
            done = ChatResponse(
                chat_log_id=chat_log_id,
                answer="".join(answer_parts),
                status=status,
                citations=citations,
            )
            yield _event("done", done.model_dump(mode="json"))
    except AppError as error:
        status = AnswerStatus.ERROR
        logger.error("chat_failed", code=error.code, detail=error.message)
        yield _event("error", {"code": error.code, "detail": _public_detail(error.code)})
    except Exception as error:  # last-resort guard: logged and surfaced generically
        status = AnswerStatus.ERROR
        logger.error("chat_unexpected", error=str(error))
        yield _event(
            "error", {"code": "INTERNAL_ERROR", "detail": _public_detail("INTERNAL_ERROR")}
        )
    finally:
        # Persist the turn if the success path didn't (client disconnect or error),
        # shielded so a disconnect cancellation can't drop the audit record. No
        # `yield` here — terminal events are emitted above, never from `finally`.
        if not persisted:
            try:
                await asyncio.shield(
                    _persist(
                        body,
                        effective_language,
                        answer_parts,
                        status,
                        citations,
                        retrieved_ids,
                        usage,
                        started,
                        settings.chat_model,
                    )
                )
            except Exception as error:
                logger.error("chat_persist_failed", error=str(error))


async def _persist(
    body: ChatRequest,
    language: Language,
    answer_parts: list[str],
    status: AnswerStatus,
    citations: list[Citation],
    retrieved_ids: list[int],
    usage: TokenUsage,
    started: float,
    model: str,
) -> int:
    """Persist a turn; raises on failure so the caller can surface it (fail loud)."""

    return await insert_chat_log(
        session_id=body.session_id,
        question=body.question,
        answer="".join(answer_parts),
        language=language,
        status=status,
        citations=citations,
        retrieved_ids=retrieved_ids,
        model=model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        latency_ms=int((time.monotonic() - started) * 1000),
    )


def _public_detail(code: str) -> str:
    return _PUBLIC_DETAIL.get(code, _PUBLIC_DETAIL["INTERNAL_ERROR"])


def _event(event: str, data: dict[str, Any]) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}
