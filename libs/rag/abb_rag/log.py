import logging
from typing import cast

import structlog
from structlog.typing import FilteringBoundLogger


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog for JSON output. Call once at process startup."""

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    # structlog.get_logger is typed as Any; cast to the configured logger type.
    return cast(FilteringBoundLogger, structlog.get_logger(name))
