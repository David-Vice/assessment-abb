from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from abb_contracts import Corpus
from abb_rag import ingest_corpus

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


async def _ingest(corpus_path: Path) -> None:
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


def _score_ragas(rows: list[dict[str, object]]) -> dict[str, float | None]:
    if not rows:
        return {}

    from datasets import Dataset
    from ragas import evaluate
    from ragas.dataset_schema import EvaluationResult
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    dataset = Dataset.from_list(rows)
    raw = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    if not isinstance(raw, EvaluationResult):
        return {}
    return {name: float(value) for name, value in raw._repr_dict.items()}


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
        ragas = _score_ragas(ragas_rows(items))

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
        help="Optional corpus.json to ingest before evaluation",
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
    args = parser.parse_args()

    _configure_event_loop()
    json_path, md_path = asyncio.run(
        run_eval(
            golden_path=args.golden_set,
            output_dir=args.output_dir,
            corpus_path=args.corpus,
            skip_ragas=args.skip_ragas,
            stem=args.stem,
        )
    )
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
