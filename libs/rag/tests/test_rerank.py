from collections.abc import Sequence

import pytest
from abb_contracts import Language, Segment
from abb_rag import rerank as rerank_module
from abb_rag.models import RetrievedChunk


class _FakeCrossEncoder:
    def __init__(self, scores: Sequence[float]) -> None:
        self._scores = scores

    def predict(self, pairs: object) -> Sequence[float]:
        return self._scores


def _candidate(chunk_id: int, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        content=content,
        url="https://abb-bank.az/en/x",
        language=Language.EN,
        segment=Segment.OTHER,
        title=None,
        score=0.0,
    )


async def test_rerank_orders_by_model_score_and_truncates(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange — model ranks b (0.9) > c (0.5) > a (0.1).
    candidates = [_candidate(1, "a"), _candidate(2, "b"), _candidate(3, "c")]
    monkeypatch.setattr(rerank_module, "_load_model", lambda: _FakeCrossEncoder([0.1, 0.9, 0.5]))

    # Act
    result = await rerank_module.rerank("q", candidates, top_k=2)

    # Assert
    assert [c.chunk_id for c in result] == [2, 3]
    assert result[0].score == pytest.approx(0.9)


async def test_rerank_empty_candidates_returns_empty() -> None:
    # Arrange & Act & Assert
    assert await rerank_module.rerank("q", [], top_k=5) == []
