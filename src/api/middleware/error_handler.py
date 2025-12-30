"""Global exception handlers and custom exceptions for FastAPI."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import traceback
from typing import Optional


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class AudioBookSyncException(Exception):
    """Base exception class for AudioBookSync API errors."""

    def __init__(self, message: str, status_code: int = 500, detail: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class AuthenticationError(AudioBookSyncException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AudioBookSyncException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class ResourceNotFoundError(AudioBookSyncException):
    """Raised when requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AudioBookSyncException):
    """Raised when there's a resource conflict (e.g., duplicate)."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class ValidationError(AudioBookSyncException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed", detail: Optional[dict] = None):
        super().__init__(
            message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class InternalServerError(AudioBookSyncException):
    """Raised for internal server errors."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================


def add_exception_handlers(app: FastAPI):
    """Register all exception handlers with the FastAPI app."""

    @app.exception_handler(AudioBookSyncException)
    async def audiobooksync_exception_handler(
        request: Request, exc: AudioBookSyncException
    ):
        """Handle custom AudioBookSync exceptions."""
        logger.error(
            f"AudioBookSync error [{exc.status_code}]: {exc.message}",
            extra={"detail": exc.detail, "path": request.url.path},
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "status_code": exc.status_code,
                **(exc.detail if exc.detail else {}),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle Pydantic validation errors."""
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(x) for x in error["loc"][1:]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        logger.warning(
            f"Validation error for {request.method} {request.url.path}",
            extra={"errors": errors},
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ValidationError",
                "message": "Request validation failed",
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        error_id = id(exc)  # Unique identifier for this error instance
        exc_type = type(exc).__name__
        exc_message = str(exc)

        logger.error(
            f"Unhandled exception [{error_id}] {exc_type}: {exc_message}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc(),
            },
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An internal server error occurred",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error_id": error_id,  # Useful for debugging
            },
        )
