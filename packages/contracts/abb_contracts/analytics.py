from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from abb_contracts.enums import Language, Segment


class TimeBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bucket: datetime
    count: int


class VolumeSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: list[TimeBucket] = Field(default_factory=list)


class TopQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    count: int


class PerformanceStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    avg_latency_ms: float
    p95_latency_ms: float
    avg_total_tokens: float
    estimated_cost_usd: float


class QualityStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answered: int
    declined_off_topic: int
    error: int


class DistributionStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    by_language: dict[Language, int] = Field(default_factory=dict)
    by_segment: dict[Segment, int] = Field(default_factory=dict)


class AnalyticsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_questions: int
    answered_rate: float
    avg_latency_ms: float
