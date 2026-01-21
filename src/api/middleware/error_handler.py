"""Global exception handlers and custom exceptions for FastAPI."""

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import traceback
from typing import Optional, Callable, Any, TypeVar
from functools import wraps
import inspect

F = TypeVar("F", bound=Callable[..., Any])


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
# DECORATORS
# ============================================================================


def handle_route_errors(operation_name: str = None) -> Callable:
    """
    Decorator for FastAPI route handlers that provides centralized error handling.

    Wraps async route handlers to catch exceptions, log them appropriately, and
    return standardized error responses. HTTPException instances are re-raised
    as-is. AudioBookSyncException subclasses are re-raised. All other exceptions
    are logged with full context and converted to 500 Internal Server Error.

    Args:
        operation_name: Optional human-readable name for the operation (for logging).
                       If not provided, uses the function name.

    Usage:
        @router.post("/items/")
        @handle_route_errors("create item")
        async def create_item(item_data: ItemCreate, db: AsyncSession) -> ItemResponse:
            # No need for try-except, the decorator handles it
            result = await db_service.create(db, item_data)
            await db.commit()
            return result

    Example of cleaned-up code:
        # BEFORE (15 lines of boilerplate per handler)
        try:
            logger.info(f"Creating item...")
            result = await service.create(db, data)
            await db.commit()
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating item: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create item",
            )

        # AFTER (decorator removes all boilerplate)
        @handle_route_errors("create item")
        async def create_item(...):
            result = await service.create(db, data)
            await db.commit()
            return result
    """

    def decorator(func: F) -> F:
        op_name = operation_name or func.__name__

        # Check if it's an async function
        if not inspect.iscoroutinefunction(func):
            raise TypeError(
                f"@handle_route_errors can only decorate async functions. "
                f"'{func.__name__}' is not async."
            )

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise FastAPI HTTPExceptions as-is
                raise
            except AudioBookSyncException:
                # Re-raise our custom exceptions as-is
                raise
            except Exception as e:
                # Log all other exceptions with full context
                logger.error(
                    f"Error during {op_name}: {type(e).__name__}: {str(e)}",
                    extra={"function": func.__name__, "traceback": traceback.format_exc()},
                )
                # Raise a generic 500 error
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to {op_name}",
                )

        return wrapper  # type: ignore

    return decorator


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
                "detail": exc.message,
                "error": exc.__class__.__name__,
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
