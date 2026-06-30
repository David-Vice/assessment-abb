from enum import StrEnum


class Language(StrEnum):
    AZ = "az"
    EN = "en"
    RU = "ru"


class Segment(StrEnum):
    INDIVIDUALS = "individuals"
    BUSINESS = "business"
    ABOUT = "about"
    OTHER = "other"


class IngestionState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    DECLINED_OFF_TOPIC = "declined_off_topic"
    DECLINED_INJECTION = "declined_injection"
    ERROR = "error"
