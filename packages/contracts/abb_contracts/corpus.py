from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from abb_contracts.enums import Language, Segment

HTTP_URL_PATTERN = r"^https?://"


class CorpusDocument(BaseModel):
    """A single scraped, cleaned page from the ABB website."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(pattern=HTTP_URL_PATTERN)
    language: Language
    segment: Segment = Segment.OTHER
    title: str | None = None
    markdown: str
    content_hash: str
    fetched_at: datetime


class Corpus(BaseModel):
    """The full uploaded artifact produced by the scraper."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    source: str
    generated_at: datetime
    documents: list[CorpusDocument] = Field(default_factory=list)
