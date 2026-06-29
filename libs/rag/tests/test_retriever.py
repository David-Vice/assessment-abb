from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

import pytest
from abb_contracts import Language
from abb_rag import retriever as retriever_module
from abb_rag.retriever import hybrid_search


def _row(chunk_id: int, language: str = "en") -> SimpleNamespace:
    return SimpleNamespace(
        id=chunk_id,
        content=f"body {chunk_id}",
        language=language,
        segment="other",
        url=f"https://abb-bank.az/{chunk_id}",
        title="T",
    )


class _Result:
    def __init__(self, rows: Sequence[SimpleNamespace]) -> None:
        self._rows = rows

    def all(self) -> Sequence[SimpleNamespace]:
        return self._rows


class _FakeSession:
    """Returns canned row batches in execute() call order."""

    def __init__(self, batches: Sequence[Sequence[SimpleNamespace]]) -> None:
        self._batches = list(batches)
        self._index = 0

    async def execute(self, sql: Any, params: dict[str, Any]) -> _Result:
        rows = self._batches[self._index]
        self._index += 1
        return _Result(rows)


@pytest.fixture(autouse=True)
def _fake_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_embed_query(text: str) -> list[float]:
        return [0.1] * 8

    monkeypatch.setattr(retriever_module, "embed_query", fake_embed_query)


async def test_hybrid_search_fuses_dense_and_sparse_with_rrf() -> None:
    # Arrange — dense ranks [1,2,3]; sparse ranks [2,3,4]; overlap (2,3) should win.
    dense = [_row(1), _row(2), _row(3)]
    sparse = [_row(2), _row(3), _row(4)]
    session = _FakeSession([dense, sparse])  # language=None → no fallback queries

    # Act
    hits = await hybrid_search(session, "q", None, candidates=10)  # type: ignore[arg-type]

    # Assert
    ids = [hit.chunk_id for hit in hits]
    assert set(ids) == {1, 2, 3, 4}
    assert ids.index(2) < ids.index(1)
    assert ids.index(3) < ids.index(4)


async def test_hybrid_search_language_fallback_fills_only_the_deficit() -> None:
    # Arrange — language-filtered branches return 1 row each (< limit 3); the
    # fallback (lang=None) tops each branch up, capped at the limit.
    session = _FakeSession(
        [
            [_row(1, "en")],  # dense primary
            [_row(1, "en"), _row(5, "az"), _row(6, "ru")],  # dense fallback
            [_row(2, "en")],  # sparse primary
            [_row(2, "en"), _row(7, "az"), _row(8, "ru")],  # sparse fallback
        ]
    )

    # Act
    hits = await hybrid_search(session, "q", Language.EN, candidates=3)  # type: ignore[arg-type]

    # Assert — deficit filled (more than the 2 same-language hits) and capped.
    ids = {hit.chunk_id for hit in hits}
    assert len(hits) == 3
    assert 1 in ids and 2 in ids
