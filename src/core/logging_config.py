"""Logging configuration for AudioBookSync."""

import sys
from typing import TYPE_CHECKING, Optional

from loguru import logger

if TYPE_CHECKING:
    from src.core.database_logging_sink import DatabaseLoggingSink

# Global database sink instance
_db_sink: Optional["DatabaseLoggingSink"] = None


def configure_logging(log_level: str = "INFO", enable_database: bool = True) -> None:
    """
    Configure loguru with stderr and optional database output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_database: Whether to enable database logging (default: True)
    """
    global _db_sink

    logger.remove()

    # Always add stderr handler
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level}</level> | "
            "<level>{message}</level>"
        ),
    )

    # Add database sink if enabled
    if enable_database:
        try:
            from src.core.database_logging_sink import DatabaseLoggingSink

            _db_sink = DatabaseLoggingSink()
            _db_sink.start()

            # Create a wrapper sink function for loguru
            # Loguru passes a message object with a .record attribute
            def db_sink_wrapper(message):
                """Wrapper to convert loguru Message to our sink format."""
                _db_sink.write(message)

            logger.add(
                db_sink_wrapper,
                level=log_level,
                format="{message}",  # Format string (unused, we access record directly)
            )
        except Exception as e:
            logger.warning(f"Failed to configure database logging: {e}. Using file logging only.")


def shutdown_logging() -> None:
    """Flush remaining logs and shutdown the database sink."""
    global _db_sink

    if _db_sink:
        try:
            _db_sink.stop()
        except Exception as e:
            logger.error(f"Error shutting down database logging sink: {e}", exc_info=True)
        finally:
            _db_sink = None
