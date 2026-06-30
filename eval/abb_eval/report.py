from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from abb_eval.models import EvalReport, GuardrailMetrics, ItemResult


def build_report(
    items: list[ItemResult],
    guardrail: GuardrailMetrics,
    ragas: dict[str, float | None] | None = None,
) -> EvalReport:
    return EvalReport(
        generated_at=datetime.now(tz=UTC).isoformat(),
        golden_count=len(items),
        guardrail=guardrail,
        ragas=ragas or {},
        items=items,
    )


def write_report(report: EvalReport, output_dir: Path, stem: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"

    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    return json_path, md_path


def _markdown(report: EvalReport) -> str:
    lines = [
        "# ABB RAG evaluation report",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Golden items: **{report.golden_count}**",
        "",
        "## Guardrail (off-topic + injection)",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Precision | {report.guardrail.precision:.3f} |",
        f"| Recall | {report.guardrail.recall:.3f} |",
        f"| TP / FP / FN | {report.guardrail.tp} / {report.guardrail.fp} / {report.guardrail.fn} |",
        "",
    ]

    if report.ragas:
        lines.extend(["## RAGAS (answerable items)", "", "| Metric | Score |", "| --- | --- |"])
        for name, score in sorted(report.ragas.items()):
            value = "n/a" if score is None else f"{score:.3f}"
            lines.append(f"| {name} | {value} |")
        lines.append("")

    latencies = [row.latency_ms for row in report.items if row.latency_ms]
    if latencies:
        latencies_sorted = sorted(latencies)
        p95_index = max(0, int(len(latencies_sorted) * 0.95) - 1)
        lines.extend(
            [
                "## Latency (ms)",
                "",
                f"- Average: **{sum(latencies) / len(latencies):.0f}**",
                f"- p95: **{latencies_sorted[p95_index]}**",
                "",
            ]
        )

    lines.extend(["## Per-question results", ""])
    for row in report.items:
        status = "answered" if row.answered else row.verdict
        lines.append(f"### `{row.id}` ({row.kind.value}) — {status}")
        lines.append("")
        lines.append(f"**Q:** {row.question}")
        if row.error:
            lines.append(f"**Error:** {row.error}")
        elif row.answer:
            preview = row.answer.replace("\n", " ")
            lines.append(f"**A:** {preview[:400]}{'…' if len(preview) > 400 else ''}")
        lines.append("")

    return "\n".join(lines)
