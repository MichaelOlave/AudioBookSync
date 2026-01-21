"""Progress callback utilities for async operations.

This module provides infrastructure for progress tracking and broadcasting
in long-running operations (download, decrypt, sync). It centralizes the
error handling pattern that was previously duplicated 13 times throughout
the codebase.
"""

from typing import Any, Awaitable, Callable, Optional, Protocol

from loguru import logger


class ProgressCallback(Protocol):
    """Type definition for progress callbacks.

    Defines the interface for async callable progress callbacks
    used throughout the application for broadcasting progress updates
    to WebSocket clients or other consumers.

    Example:
        async def my_callback(event_type: str, **kwargs: Any) -> None:
            await ws_manager.broadcast_to_user(
                user_id=kwargs["user_id"],
                event_type=event_type,
                data=kwargs,
            )

        await safe_progress_callback(
            my_callback,
            event_type="download.started",
            asin="B12345",
            title="Test Book",
        )
    """

    async def __call__(self, event_type: str, **kwargs: Any) -> None:
        """Invoke progress callback with event details.

        Args:
            event_type: Type of progress event (e.g., "download.started")
            **kwargs: Event-specific data (asin, title, error, etc.)
        """
        ...


async def safe_progress_callback(
    callback: Optional[Callable[..., Awaitable[Any]]],
    event_type: str,
    **kwargs: Any,
) -> None:
    """Safely invoke progress callback with error handling.

    This helper eliminates the need for try/except blocks around every
    progress callback invocation. It was previously duplicated 13 times:
    - downloader.py: 4 occurrences (lines 45-53, 91-99, 114-124, 130-140)
    - decryptor.py: 4 occurrences (lines 46-54, 94-102, 118-128)
    - library_sync.py: 5 occurrences (lines 174-182, 190-198, 201-209, 217-225, 233-242)

    By centralizing error handling, we:
    1. Eliminate ~130 lines of duplicated code
    2. Make error handling consistent across all operations
    3. Simplify call sites (1 line instead of 10)
    4. Enable easy logging/monitoring of callback failures

    Args:
        callback: Optional async callable for progress updates.
                 If None, this function returns immediately without error.
        event_type: Event type string (e.g., "download.started", "decrypt.completed")
        **kwargs: Event-specific data passed to callback (asin, title, error, etc.)

    Example:
        # OLD (10 lines per occurrence, repeated 13 times)
        if progress_callback:
            try:
                await progress_callback(
                    event_type="download.started",
                    asin=book_asin,
                    filename=book_title,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast download.started: {e}")

        # NEW (1 line)
        await safe_progress_callback(
            progress_callback,
            event_type="download.started",
            asin=book_asin,
            filename=book_title,
        )
    """
    if callback is None:
        return

    try:
        await callback(event_type=event_type, **kwargs)
    except Exception as e:
        logger.warning(f"Failed to broadcast {event_type}: {e}")
