import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from abb_contracts import AnswerStatus, ChatRequest, ChatResponse, ChatTurn, Citation
from abb_rag import AppError, get_logger, get_settings, retrieve, session_scope
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from abb_chat.context import build_context, to_citations
from abb_chat.generation import stream_answer
from abb_chat.guardrail import Verdict, classify
from abb_chat.memory import load_history, rewrite_query
from abb_chat.persistence import fetch_recent_turns, insert_chat_log
from abb_chat.prompts import off_topic_refusal

logger = get_logger(__name__)
router = APIRouter(tags=["chat"])

SSE_PING_SECONDS = 15
SESSION_HISTORY_LIMIT = 50


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
    status = AnswerStatus.ANSWERED

    try:
        verdict = await classify(body.question)
        if verdict is not Verdict.ON_TOPIC:
            status = AnswerStatus.DECLINED_OFF_TOPIC
            refusal = off_topic_refusal(body.language)
            answer_parts.append(refusal)
            logger.info("chat_declined", verdict=verdict.value, language=body.language.value)
            yield _event("token", {"token": refusal})
            return

        history = await load_history(body.session_id) if settings.chat_memory_enabled else []
        search_query = await rewrite_query(body.question, history) if history else body.question
        async with session_scope() as session:
            chunks = await retrieve(session, search_query, body.language)
        retrieved_ids = [chunk.chunk_id for chunk in chunks]
        citations = to_citations(chunks)
        context = build_context(chunks, settings.context_token_budget)

        async for token in stream_answer(body.question, body.language, context, history):
            if await request.is_disconnected():
                break
            answer_parts.append(token)
            yield _event("token", {"token": token})
    except AppError as error:
        status = AnswerStatus.ERROR
        logger.error("chat_failed", code=error.code, detail=error.message)
        yield _event("error", {"code": error.code, "detail": error.message})
    except Exception as error:  # last-resort guard: logged and surfaced as a generic error
        status = AnswerStatus.ERROR
        logger.error("chat_unexpected", error=str(error))
        yield _event("error", {"code": "INTERNAL_ERROR", "detail": "unexpected error"})
    finally:
        answer = "".join(answer_parts)
        latency_ms = int((time.monotonic() - started) * 1000)
        # Shielded so a mid-stream disconnect still persists the turn.
        chat_log_id = await asyncio.shield(
            _persist(
                body, answer, status, citations, retrieved_ids, latency_ms, settings.chat_model
            )
        )
        if not await request.is_disconnected():
            done = ChatResponse(
                chat_log_id=chat_log_id, answer=answer, status=status, citations=citations
            )
            yield _event("done", done.model_dump(mode="json"))


async def _persist(
    body: ChatRequest,
    answer: str,
    status: AnswerStatus,
    citations: list[Citation],
    retrieved_ids: list[int],
    latency_ms: int,
    model: str,
) -> int:
    try:
        return await insert_chat_log(
            session_id=body.session_id,
            question=body.question,
            answer=answer,
            language=body.language,
            status=status,
            citations=citations,
            retrieved_ids=retrieved_ids,
            model=model,
            latency_ms=latency_ms,
        )
    except Exception as error:  # persistence failures must not break the response
        logger.error("chat_persist_failed", error=str(error))
        return 0


def _event(event: str, data: dict[str, Any]) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}
