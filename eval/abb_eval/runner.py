from __future__ import annotations

import time
from pathlib import Path

from abb_chat.context import build_context
from abb_chat.generation import TokenUsage, stream_answer
from abb_chat.guardrail import Verdict, classify
from abb_chat.lang_detect import auto_language
from abb_chat.prompts import off_topic_refusal
from abb_contracts import Language
from abb_rag import get_settings, retrieve, session_scope

from abb_eval.models import GoldenItem, GoldenKind, GoldenSet, GuardrailMetrics, ItemResult

_PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_GOLDEN_SET = _PACKAGE_DIR / "golden_set.json"


def load_golden_set(path: Path | None = None) -> GoldenSet:
    source = path or DEFAULT_GOLDEN_SET
    return GoldenSet.model_validate_json(source.read_text(encoding="utf-8"))


async def run_item(item: GoldenItem) -> ItemResult:
    started = time.monotonic()
    hint = Language(item.language)
    effective = auto_language(item.question, hint=hint)

    try:
        verdict = await classify(item.question)
    except Exception as error:  # pragma: no cover - surfaced in report
        return ItemResult(
            id=item.id,
            kind=item.kind,
            question=item.question,
            language=effective.value,
            verdict="error",
            answered=False,
            latency_ms=_elapsed_ms(started),
            error=str(error),
        )

    if verdict is not Verdict.ON_TOPIC:
        refusal = off_topic_refusal(effective)
        return ItemResult(
            id=item.id,
            kind=item.kind,
            question=item.question,
            language=effective.value,
            verdict=verdict.value,
            answered=False,
            answer=refusal,
            ground_truth=item.ground_truth,
            latency_ms=_elapsed_ms(started),
        )

    settings = get_settings()
    async with session_scope() as session:
        chunks = await retrieve(session, item.question, effective)
    context = build_context(chunks, settings.context_token_budget)
    usage = TokenUsage()
    parts: list[str] = []
    async for token in stream_answer(item.question, effective, context, [], usage):
        parts.append(token)

    return ItemResult(
        id=item.id,
        kind=item.kind,
        question=item.question,
        language=effective.value,
        verdict=verdict.value,
        answered=True,
        answer="".join(parts),
        contexts=[chunk.content for chunk in chunks],
        ground_truth=item.ground_truth,
        latency_ms=_elapsed_ms(started),
    )


def guardrail_metrics(items: list[ItemResult]) -> GuardrailMetrics:
    """Precision/recall for blocking off-topic and injection probes."""

    blocked_kinds = {GoldenKind.OFFTOPIC, GoldenKind.INJECTION}
    tp = fp = fn = 0

    for row in items:
        should_block = row.kind in blocked_kinds
        blocked = row.verdict != Verdict.ON_TOPIC.value

        if should_block and blocked:
            tp += 1
        elif should_block and not blocked:
            fn += 1
        elif not should_block and blocked:
            fp += 1

    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return GuardrailMetrics(precision=precision, recall=recall, tp=tp, fp=fp, fn=fn)


def ragas_rows(items: list[ItemResult]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in items:
        if row.kind is not GoldenKind.ANSWERABLE or not row.answered:
            continue
        if not row.answer or not row.ground_truth:
            continue
        rows.append(
            {
                "question": row.question,
                "answer": row.answer,
                "contexts": row.contexts,
                "ground_truth": row.ground_truth,
            }
        )
    return rows


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
