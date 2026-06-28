class AppError(Exception):
    """Base typed error. Carries an HTTP status and a stable machine code."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)
        self.message = message or self.code


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class InputValidationError(AppError):
    """Distinct from pydantic.ValidationError to avoid name collisions."""

    status_code = 400
    code = "VALIDATION_ERROR"


class ExternalServiceError(AppError):
    """Wraps failures from OpenAI / LangChain / Redis with a safe message."""

    status_code = 502
    code = "UPSTREAM_ERROR"
