"""Background sync service for library synchronization."""

from typing import Optional
from datetime import datetime
from loguru import logger

from ...database.db_sync import sync_ops
from ..websockets import ws_manager, EventType


class SyncService:
    """Service for orchestrating background sync operations.

    Handles library synchronization including:
    - Fetching books from Audible
    - Adding books to database
    - Downloading audiobook files
    - Decrypting audiobook files
    - Tracking progress and status
    - Sending real-time updates via WebSocket
    """

    @staticmethod
    async def start_sync(
        user_id: str,
        sync_id: str,
        sync_type: str = "full",
    ) -> None:
        """
        Start a background sync operation.

        This is the main orchestration method that coordinates:
        1. Broadcast sync.started event
        2. Fetch library from Audible
        3. Process each book (download + decrypt)
        4. Broadcast progress updates
        5. Complete sync with final statistics

        Args:
            user_id: User UUID performing the sync
            sync_id: Unique sync identifier
            sync_type: Type of sync (full, incremental, manual)

        Note:
            This should be run as a background task via FastAPI BackgroundTasks
            or a task queue like Celery for production use.
        """
        try:
            logger.info(
                f"Starting sync {sync_id} for user {user_id} (type: {sync_type})"
            )

            # Broadcast sync started event
            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.SYNC_STARTED.value,
                data={
                    "sync_id": sync_id,
                    "sync_type": sync_type,
                    "timestamp": datetime.utcnow().timestamp(),
                },
            )

            # Initialize sync statistics
            stats = {
                "books_found": 0,
                "books_added": 0,
                "books_downloaded": 0,
                "books_decrypted": 0,
                "errors_count": 0,
            }

            # Define progress callback for library sync
            async def sync_progress_callback(**kwargs):
                """Wrapper to pass sync_id to broadcast_progress."""
                await SyncService.broadcast_progress(
                    sync_id=sync_id,
                    user_id=user_id,
                    **kwargs,
                )

            # Execute actual library sync with user context and progress tracking
            from ...operations.library_sync import sync_library

            await sync_library(
                user_id=user_id,
                ws_broadcast_fn=sync_progress_callback,
            )

            logger.info(f"Sync {sync_id} completed successfully")

            # Complete sync with statistics
            await SyncService.complete_sync(
                sync_id=sync_id,
                user_id=user_id,
                status="completed",
                stats=stats,
            )

        except Exception as e:
            logger.error(f"Sync {sync_id} failed: {e}")
            await SyncService.fail_sync(
                sync_id=sync_id,
                user_id=user_id,
                error=str(e),
            )

    @staticmethod
    async def complete_sync(
        sync_id: str,
        user_id: str,
        status: str,
        stats: dict,
    ) -> None:
        """
        Complete a sync operation with final statistics.

        Args:
            sync_id: Unique sync identifier
            user_id: User UUID
            status: Final status (completed, partial, failed)
            stats: Dictionary with sync statistics

        Updates the sync record in database and broadcasts completion event.
        """
        try:
            logger.info(f"Completing sync {sync_id} with status {status}")

            # Update sync record in database
            success = sync_ops.complete_sync_history(
                sync_id=sync_id,
                status=status,
                books_found=stats.get("books_found", 0),
                books_added=stats.get("books_added", 0),
                books_downloaded=stats.get("books_downloaded", 0),
                books_decrypted=stats.get("books_decrypted", 0),
                errors_count=stats.get("errors_count", 0),
                notes=stats.get("notes"),
            )

            if not success:
                logger.error(f"Failed to update sync record {sync_id}")
                return

            # Get final sync record
            sync = sync_ops.get_sync_by_id(sync_id)
            if not sync:
                logger.error(f"Sync record not found: {sync_id}")
                return

            # Broadcast sync completed event
            duration = sync.get("duration_seconds", 0.0) or 0.0
            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.SYNC_COMPLETED.value,
                data={
                    "sync_id": sync_id,
                    "status": status,
                    "books_found": sync.get("books_found", 0),
                    "books_added": sync.get("books_added", 0),
                    "books_downloaded": sync.get("books_downloaded", 0),
                    "books_decrypted": sync.get("books_decrypted", 0),
                    "errors_count": sync.get("errors_count", 0),
                    "duration_seconds": duration,
                    "timestamp": datetime.utcnow().timestamp(),
                },
            )

            logger.info(f"Sync {sync_id} completed and broadcast sent")

        except Exception as e:
            logger.error(f"Error completing sync {sync_id}: {e}")

    @staticmethod
    async def fail_sync(
        sync_id: str,
        user_id: str,
        error: str,
        error_code: Optional[str] = None,
    ) -> None:
        """
        Mark a sync as failed.

        Args:
            sync_id: Unique sync identifier
            user_id: User UUID
            error: Error message
            error_code: Optional error code for categorization

        Updates the sync record and broadcasts failure event.
        """
        try:
            logger.error(f"Failing sync {sync_id}: {error}")

            # Mark as failed in database
            success = sync_ops.complete_sync_history(
                sync_id=sync_id,
                status="failed",
                notes=f"Sync failed: {error}",
            )

            if not success:
                logger.error(f"Failed to update sync record {sync_id}")
                return

            # Broadcast sync failed event
            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.SYNC_FAILED.value,
                data={
                    "sync_id": sync_id,
                    "error": error,
                    "error_code": error_code or "UNKNOWN_ERROR",
                    "timestamp": datetime.utcnow().timestamp(),
                },
            )

            logger.info(f"Sync {sync_id} failure broadcast sent")

        except Exception as e:
            logger.error(f"Error failing sync {sync_id}: {e}")

    @staticmethod
    async def broadcast_progress(
        sync_id: str,
        user_id: str,
        current_book: Optional[str] = None,
        books_processed: int = 0,
        books_total: int = 0,
        progress_percent: float = 0.0,
    ) -> None:
        """
        Broadcast sync progress update.

        Args:
            sync_id: Unique sync identifier
            user_id: User UUID
            current_book: ASIN of book currently being processed
            books_processed: Number of books processed so far
            books_total: Total number of books to process
            progress_percent: Overall progress percentage (0-100)

        Sends real-time progress update via WebSocket to connected clients.
        """
        try:
            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.SYNC_PROGRESS.value,
                data={
                    "sync_id": sync_id,
                    "current_book": current_book,
                    "books_processed": books_processed,
                    "books_total": books_total,
                    "progress_percent": progress_percent,
                    "status": "in_progress",
                    "timestamp": datetime.utcnow().timestamp(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast progress for sync {sync_id}: {e}")

    @staticmethod
    async def broadcast_download_progress(
        user_id: str,
        asin: str,
        filename: str,
        bytes_downloaded: int = 0,
        total_bytes: int = 0,
        speed_kbps: float = 0.0,
    ) -> None:
        """
        Broadcast download progress update.

        Args:
            user_id: User UUID
            asin: Book ASIN
            filename: Download filename
            bytes_downloaded: Bytes downloaded so far
            total_bytes: Total bytes to download
            speed_kbps: Current download speed in KB/s

        Sends real-time download progress via WebSocket.
        """
        try:
            progress_percent = (
                (bytes_downloaded / total_bytes * 100) if total_bytes > 0 else 0.0
            )

            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.DOWNLOAD_PROGRESS.value,
                data={
                    "asin": asin,
                    "filename": filename,
                    "bytes_downloaded": bytes_downloaded,
                    "total_bytes": total_bytes,
                    "progress_percent": progress_percent,
                    "speed_kbps": speed_kbps,
                    "timestamp": datetime.utcnow().timestamp(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast download progress: {e}")


# Singleton instance
sync_service = SyncService()
