from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from abb_contracts.enums import AnswerStatus, Language, Segment

HTTP_URL_PATTERN = r"^https?://"


class Citation(BaseModel):
    """A source chunk backing an answer, deep-linkable to the ABB page."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(pattern=HTTP_URL_PATTERN)
    title: str | None = None
    language: Language
    segment: Segment = Segment.OTHER
    snippet: str | None = None


class ChatRequest(BaseModel):
    """Input contract of the question-handling microservice."""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    question: str = Field(min_length=1, max_length=2000)
    language: Language = Language.EN


class ChatResponse(BaseModel):
    """Output contract returned on stream completion."""

    model_config = ConfigDict(extra="forbid")

    chat_log_id: int
    answer: str
    status: AnswerStatus
    citations: list[Citation] = Field(default_factory=list)


class ChatTurn(BaseModel):
    """A persisted question/answer turn (used for session hydration)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    session_id: UUID
    question: str
    answer: str
    language: Language | None = None
    status: AnswerStatus
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime
