from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from abb_contracts import Corpus
from abb_rag import ingest_corpus
from abb_rag.settings import get_settings

from abb_eval.models import GoldenItem, ItemResult
from abb_eval.report import build_report, write_report
from abb_eval.runner import (
    DEFAULT_GOLDEN_SET,
    guardrail_metrics,
    load_golden_set,
    ragas_rows,
    run_item,
)


def _configure_event_loop() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _disable_rerank() -> None:
    os.environ["RERANK_ENABLED"] = "false"
    get_settings.cache_clear()


def _ensure_rerank_ready() -> None:
    """Fail fast when rerank is enabled but sentence-transformers is missing."""
    settings = get_settings()
    if not settings.rerank_enabled:
        return
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        print(
            "RERANK_ENABLED=true but sentence-transformers is not installed.\n"
            "Rebuild the eval image after chat (keeps the rerank extra):\n"
            "  docker compose build chat\n"
            "  docker compose --profile eval build eval\n"
            "Or pass --no-rerank for a quick run without cross-encoder reranking.",
            file=sys.stderr,
        )
        sys.exit(1)


def _normalize_container_path(path: Path) -> Path:
    """Undo Git Bash path mangling (`/app/...` → `C:/Program Files/Git/app/...`)."""
    text = path.as_posix()
    marker = "/Program Files/Git/app/"
    if marker in text:
        return Path("/app") / path.name
    return path


async def _ingest(corpus_path: Path) -> None:
    corpus_path = _normalize_container_path(corpus_path)
    raw = await asyncio.to_thread(corpus_path.read_text, encoding="utf-8")
    corpus = Corpus.model_validate_json(raw)
    indexed = await ingest_corpus(corpus)
    print(f"indexed chunks: {indexed}")


async def _run_all(items: list[GoldenItem]) -> list[ItemResult]:
    results = []
    for index, item in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] {item.id} …", flush=True)
        results.append(await run_item(item))
    return results


_RAGAS_METRICS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


def _extract_ragas_scores(raw: Any) -> dict[str, float | None]:
    from ragas.utils import safe_nanmean

    scores: dict[str, float | None] = {}
    for name in _RAGAS_METRICS:
        try:
            value = safe_nanmean(raw[name])
        except KeyError:
            continue
        if value is None:
            scores[name] = None
        else:
            scores[name] = float(value)
    return scores


def _score_ragas(rows: list[dict[str, object]]) -> dict[str, float | None]:
    if not rows:
        return {}

    from datasets import Dataset
    from langchain_openai import OpenAIEmbeddings as LangchainOpenAIEmbeddings
    from openai import OpenAI
    from ragas import evaluate
    from ragas.dataset_schema import EvaluationResult
    from ragas.embeddings.base import LangchainEmbeddingsWrapper
    from ragas.llms import llm_factory
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    settings = get_settings()
    api_key = settings.openai_api_key.get_secret_value()
    if not api_key:
        print("OPENAI_API_KEY not set; cannot run RAGAS scoring.", file=sys.stderr)
        return {}

    # RAGAS auto-default embeddings use the modern provider API (embed_text), but
    # answer_relevancy still calls embed_query — pass LangChain wrappers explicitly.
    client = OpenAI(api_key=api_key)
    llm = llm_factory(settings.aux_model, client=client)
    embeddings = LangchainEmbeddingsWrapper(
        LangchainOpenAIEmbeddings(model=settings.embedding_model, api_key=api_key)  # type: ignore[call-arg]
    )

    dataset = Dataset.from_list(rows)
    raw = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,  # type: ignore[arg-type]
        embeddings=embeddings,
    )
    if not isinstance(raw, EvaluationResult):
        print(f"Unexpected RAGAS result type: {type(raw)!r}", file=sys.stderr)
        return {}
    return _extract_ragas_scores(raw)


async def run_eval(
    *,
    golden_path: Path,
    output_dir: Path,
    corpus_path: Path | None,
    skip_ragas: bool,
    stem: str | None,
) -> tuple[Path, Path]:
    if corpus_path is not None:
        await _ingest(corpus_path)

    golden = load_golden_set(golden_path)
    items = await _run_all(golden.items)
    guardrail = guardrail_metrics(items)

    ragas: dict[str, float | None] = {}
    if not skip_ragas:
        rows = ragas_rows(items)
        if not rows:
            print("No answered golden-set items to score with RAGAS.", file=sys.stderr)
            sys.exit(1)
        ragas = _score_ragas(rows)
        if not ragas:
            print("RAGAS scoring produced no metrics.", file=sys.stderr)
            sys.exit(1)

    report = build_report(items, guardrail, ragas)
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return write_report(report, output_dir, stem or f"eval-{timestamp}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ABB RAG golden-set evaluation.")
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=DEFAULT_GOLDEN_SET,
        help="Path to golden_set.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("eval/results"),
        help="Directory for JSON + Markdown reports",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=None,
        help="Optional corpus.json to ingest first (in Docker use corpus.sample.json)",
    )
    parser.add_argument(
        "--skip-ragas",
        action="store_true",
        help="Skip RAGAS scoring (guardrail + latency only)",
    )
    parser.add_argument(
        "--stem",
        default=None,
        help="Output filename stem (default: eval-<timestamp>)",
    )
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Disable cross-encoder rerank (quick local run; scores differ from prod)",
    )
    args = parser.parse_args()

    if args.no_rerank:
        _disable_rerank()
    _ensure_rerank_ready()
    settings = get_settings()
    if settings.rerank_enabled:
        print("rerank: enabled (prod-faithful retrieval)", flush=True)
    else:
        print("rerank: disabled", flush=True)
    _configure_event_loop()
    corpus_path = _normalize_container_path(args.corpus) if args.corpus else None
    output_dir = _normalize_container_path(args.output_dir)
    json_path, md_path = asyncio.run(
        run_eval(
            golden_path=args.golden_set,
            output_dir=output_dir,
            corpus_path=corpus_path,
            skip_ragas=args.skip_ragas,
            stem=args.stem,
        )
    )
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
