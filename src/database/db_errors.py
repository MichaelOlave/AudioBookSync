"""Error logging database operations."""

from typing import Optional

from loguru import logger

from .db_pool import DatabasePool  # noqa: F401
from .db_pool import db_pool as _db_pool


class ErrorOperations:
    """Database operations for error logging and tracking."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def log_error(
        self,
        error_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        asin: Optional[str] = None,
        severity: str = "error",
        **kwargs,
    ) -> bool:
        """
        Log an error to the database.

        Args:
            error_type: Type of error (download_error, decryption_error, api_error, etc.)
            error_message: Human-readable error description
            user_id: Associated user UUID (optional)
            asin: Associated book ASIN (optional)
            severity: Severity level (info, warning, error, critical)
            **kwargs: Additional data (stack_trace, context, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO error_log (
                        user_id, asin, error_type, error_message,
                        severity, stack_trace
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        user_id,
                        asin,
                        error_type,
                        error_message,
                        severity,
                        kwargs.get("stack_trace"),
                    ),
                )
                logger.info(f"Logged error: {error_type} - {error_message}")
                return True
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")
            return False


# Singleton instance
error_ops = ErrorOperations()
