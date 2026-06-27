from pydantic import BaseModel, ConfigDict

from abb_contracts.corpus import Corpus
from abb_contracts.enums import IngestionState


class IngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corpus: Corpus


class IngestionJob(BaseModel):
    """Returned immediately on upload; the job runs asynchronously."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    state: IngestionState = IngestionState.QUEUED


class IngestionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    state: IngestionState
    processed: int = 0
    total: int = 0
    error: str | None = None
