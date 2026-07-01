from pathlib import Path

from abb_eval.models import GoldenKind, GuardrailMetrics, ItemResult
from abb_eval.runner import DEFAULT_GOLDEN_SET, guardrail_metrics, load_golden_set


def test_golden_set_loads_and_has_coverage() -> None:
    golden = load_golden_set(DEFAULT_GOLDEN_SET)
    assert golden.version == 1
    assert len(golden.items) >= 25

    kinds = {item.kind for item in golden.items}
    languages = {item.language for item in golden.items}
    assert GoldenKind.ANSWERABLE in kinds
    assert GoldenKind.OFFTOPIC in kinds
    assert GoldenKind.INJECTION in kinds
    assert languages == {"az", "en", "ru"}

    answerable = [item for item in golden.items if item.kind is GoldenKind.ANSWERABLE]
    assert all(item.ground_truth for item in answerable)


def test_guardrail_metrics_perfect_block() -> None:
    items = [
        ItemResult(
            id="a",
            kind=GoldenKind.OFFTOPIC,
            question="q",
            language="en",
            verdict="off_topic",
            answered=False,
        ),
        ItemResult(
            id="b",
            kind=GoldenKind.ANSWERABLE,
            question="q",
            language="en",
            verdict="on_topic",
            answered=True,
        ),
    ]
    metrics = guardrail_metrics(items)
    assert metrics == GuardrailMetrics(precision=1.0, recall=1.0, tp=1, fp=0, fn=0)


def test_normalize_container_path_git_bash_mangling() -> None:
    from abb_eval.cli import _normalize_container_path

    mangled = Path("C:/Program Files/Git/app/corpus.sample.json")
    assert _normalize_container_path(mangled) == Path("/app/corpus.sample.json")


def test_golden_set_path_override(tmp_path: Path) -> None:
    subset = DEFAULT_GOLDEN_SET.read_text(encoding="utf-8")
    target = tmp_path / "golden.json"
    target.write_text(subset, encoding="utf-8")
    assert len(load_golden_set(target).items) >= 25
