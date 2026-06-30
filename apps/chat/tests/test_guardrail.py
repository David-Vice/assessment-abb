from types import SimpleNamespace
from typing import Any

import pytest
from abb_chat import guardrail as guardrail_module
from abb_chat.guardrail import Verdict, classify


class _FakeAuxModel:
    def __init__(self, content: str) -> None:
        self._content = content

    async def ainvoke(self, messages: Any) -> SimpleNamespace:
        return SimpleNamespace(content=self._content)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("ON_TOPIC", Verdict.ON_TOPIC),
        ("OFF_TOPIC", Verdict.OFF_TOPIC),
        ("INJECTION", Verdict.INJECTION),
        # Fail closed: unrecognized labels decline rather than pass through.
        ("something unexpected", Verdict.OFF_TOPIC),
    ],
)
async def test_classify_maps_model_label(
    monkeypatch: pytest.MonkeyPatch, label: str, expected: Verdict
) -> None:
    # Arrange
    monkeypatch.setattr(guardrail_module, "get_aux_model", lambda: _FakeAuxModel(label))

    # Act & Assert
    assert await classify("question") is expected
