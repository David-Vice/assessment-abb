from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GoldenKind(StrEnum):
    ANSWERABLE = "answerable"
    OFFTOPIC = "offtopic"
    INJECTION = "injection"


class GoldenItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    language: Literal["az", "en", "ru"]
    kind: GoldenKind
    ground_truth: str | None = None


class GoldenSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    items: list[GoldenItem] = Field(min_length=1)


class ItemResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: GoldenKind
    question: str
    language: str
    verdict: str
    answered: bool
    answer: str | None = None
    contexts: list[str] = Field(default_factory=list)
    ground_truth: str | None = None
    latency_ms: int = 0
    error: str | None = None


class GuardrailMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    precision: float
    recall: float
    tp: int
    fp: int
    fn: int


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: str
    golden_count: int
    guardrail: GuardrailMetrics
    ragas: dict[str, float | None] = Field(default_factory=dict)
    items: list[ItemResult]
