"""Background task service for orchestrating operations in background threads.

This service bridges the API layer (which uses dictionaries) with the operations layer
(which expects lists and specific formats). It handles:
- Parameter conversion between API and operations formats
- User context injection for all operations
- WebSocket progress event broadcasting
- Error handling and logging
"""

from typing import Callable, Any
from datetime import datetime, timezone
from loguru import logger

from ...database.db_downloads import download_ops
from ...database.db_decryptions import decryption_ops
from ...database.db_errors import error_ops
from ...operations.library_sync import sync_library
from ...operations.downloader import download_book
from ...operations.decryptor import decrypt_book
from ..websockets import ws_manager, EventType
from .sync_service import SyncService


class BackgroundTaskService:
    """Service for executing long-running operations as background tasks.

    Handles orchestration of:
    - Library sync from Audible
    - Individual book downloads
    - Individual book decryption
    - Progress tracking and WebSocket updates
    """

    # ===================
    # Parameter Adapters
    # ===================

    @staticmethod
    def _dict_to_book_list(book: dict) -> list:
        """
        Convert API book dictionary to operations list format.

        The operations layer expects books as [asin, title] lists.
        The API layer uses {"asin": "...", "title": "..."} dictionaries.
        This adapter ensures type safety and clear conversion.

        Args:
            book: Dictionary with at minimum {"asin": str, "title": str}

        Returns:
            List in format [asin, title]

        Raises:
            ValueError: If required fields are missing

        Example:
            >>> book_dict = {"asin": "B123456789", "title": "Example Book"}
            >>> BackgroundTaskService._dict_to_book_list(book_dict)
            ['B123456789', 'Example Book']
        """
        if "asin" not in book or "title" not in book:
            raise ValueError("Book dict must contain 'asin' and 'title' keys")

        return [book["asin"], book["title"]]

    # ============================
    # Progress Callback Factories
    # ============================

    @staticmethod
    async def _create_progress_callback(user_id: str) -> Callable:
        """
        Create a progress callback function for operations.

        The callback allows operations to report progress without directly
        depending on the WebSocket infrastructure. This maintains clean
        separation of concerns and allows operations to be tested independently.

        Args:
            user_id: User UUID for targeting WebSocket broadcasts

        Returns:
            Async function that broadcasts events to user's WebSocket connections

        Example:
            >>> callback = await BackgroundTaskService._create_progress_callback(user_id)
            >>> await callback(event_type="download.started", asin="B123")
        """

        async def broadcast_callback(event_type: str, **data: Any) -> None:
            """Broadcast progress event to user's WebSocket connections."""
            try:
                # Add timestamp if not provided
                if "timestamp" not in data:
                    data["timestamp"] = datetime.utcnow().timestamp()

                logger.debug(f"Broadcasting {event_type} for user {user_id}: {data}")
                await ws_manager.broadcast_to_user(
                    user_id=user_id,
                    event_type=event_type,
                    data=data,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast progress event {event_type}: {e}")

        return broadcast_callback

    # ==============================
    # Background Task Executors
    # ==============================

    @staticmethod
    async def execute_sync_operation(
        user_id: str,
        sync_id: str,
        sync_type: str = "full",
    ) -> None:
        """
        Execute a library sync operation in background.

        This is the main entry point for background sync tasks. It coordinates:
        1. Broadcast sync.started event
        2. Call library_sync with user context and progress callback
        3. Handle errors and update sync record
        4. Broadcast sync.completed or sync.failed event

        Args:
            user_id: User UUID performing the sync
            sync_id: Unique sync identifier
            sync_type: Type of sync ("full", "incremental", "manual")

        Note:
            This is called by FastAPI BackgroundTasks and should NOT be awaited
            directly from request handlers. Use background_tasks.add_task() instead.

        Example:
            # In a router:
            background_tasks.add_task(
                BackgroundTaskService.execute_sync_operation,
                user_id=user_id,
                sync_id=sync_id,
                sync_type="full"
            )
        """
        try:
            logger.info(f"[Sync {sync_id}] Starting sync for user {user_id}")

            # Create progress callback for broadcasting updates
            progress_callback = await BackgroundTaskService._create_progress_callback(
                user_id
            )

            # Execute actual library sync
            await sync_library(
                user_id=user_id,
                ws_broadcast_fn=progress_callback,
            )

            logger.info(f"[Sync {sync_id}] Sync completed successfully")

            # Note: sync_library() handles updating the database and broadcasting
            # the completion event, so we don't need to do it here

        except Exception as e:
            logger.error(f"[Sync {sync_id}] Sync failed: {e}", exc_info=True)

            # Log error to database
            try:
                error_ops.log_error(
                    error_type="sync_error",
                    error_message=str(e),
                    user_id=user_id,
                    severity="error",
                    context={"sync_id": sync_id, "sync_type": sync_type},
                )
            except Exception as log_err:
                logger.error(f"Failed to log sync error: {log_err}")

            # Broadcast sync failed event
            await SyncService.fail_sync(
                sync_id=sync_id,
                user_id=user_id,
                error=str(e),
                error_code="SYNC_OPERATION_FAILED",
            )

    @staticmethod
    async def execute_download_operation(
        user_id: str,
        download_id: str,
        book: dict,
    ) -> None:
        """
        Execute a single book download operation in background.

        This queues and monitors a single book download. It:
        1. Converts API dict to operations list format
        2. Updates download status to 'downloading'
        3. Calls downloader with progress callback
        4. Updates download status based on result
        5. Broadcasts download events

        Args:
            user_id: User UUID initiating the download
            download_id: Unique download identifier
            book: Book dictionary with {"asin": str, "title": str}

        Raises:
            Logs errors to database instead of raising

        Example:
            # In a router:
            background_tasks.add_task(
                BackgroundTaskService.execute_download_operation,
                user_id=user_id,
                download_id=download_id,
                book={"asin": "B123456789", "title": "Example Book"}
            )
        """
        asin = None
        try:
            # Convert API format to operations format
            book_list = BackgroundTaskService._dict_to_book_list(book)
            asin = book_list[0]
            title = book_list[1]

            logger.info(f"[Download {download_id}] Starting download for {title} ({asin})")

            # Update status to downloading
            download_ops.update_download_status(
                download_id=download_id,
                status="downloading",
            )

            # Create progress callback
            progress_callback = await BackgroundTaskService._create_progress_callback(
                user_id
            )

            # Execute download
            success = await download_book(book_list, progress_callback=progress_callback)

            if success:
                logger.info(f"[Download {download_id}] Download completed successfully")

                # Update status to completed
                download_ops.update_download_status(
                    download_id=download_id,
                    status="completed",
                )

                # Broadcast completion event
                await ws_manager.broadcast_to_user(
                    user_id=user_id,
                    event_type=EventType.DOWNLOAD_COMPLETED.value,
                    data={
                        "download_id": download_id,
                        "asin": asin,
                        "title": title,
                        "status": "completed",
                        "timestamp": datetime.utcnow().timestamp(),
                    },
                )
            else:
                logger.warning(f"[Download {download_id}] Download failed")

                # Update status to failed
                download_ops.update_download_status(
                    download_id=download_id,
                    status="failed",
                    error_message="Download operation returned false",
                )

                # Broadcast failure event
                await ws_manager.broadcast_to_user(
                    user_id=user_id,
                    event_type=EventType.DOWNLOAD_FAILED.value,
                    data={
                        "download_id": download_id,
                        "asin": asin,
                        "title": title,
                        "error": "Download operation failed",
                        "timestamp": datetime.now(timezone  .utc).timestamp(),
                    },
                )

        except ValueError as e:
            # Parameter validation error
            logger.error(f"[Download {download_id}] Invalid parameters: {e}")

            download_ops.update_download_status(
                download_id=download_id,
                status="failed",
                error_message=f"Invalid book parameters: {str(e)}",
            )

            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.DOWNLOAD_FAILED.value,
                data={
                    "download_id": download_id,
                    "asin": asin,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                },
            )

        except Exception as e:
            logger.error(
                f"[Download {download_id}] Unexpected error: {e}",
                exc_info=True,
            )

            # Update status to failed
            download_ops.update_download_status(
                download_id=download_id,
                status="failed",
                error_message=str(e),
            )

            # Log error
            try:
                error_ops.log_error(
                    error_type="download_error",
                    error_message=str(e),
                    user_id=user_id,
                    asin=asin,
                    severity="error",
                    context={"download_id": download_id},
                )
            except Exception as log_err:
                logger.error(f"Failed to log download error: {log_err}")

            # Broadcast failure
            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.DOWNLOAD_FAILED.value,
                data={
                    "download_id": download_id,
                    "asin": asin,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                },
            )

    @staticmethod
    async def execute_decrypt_operation(
        user_id: str,
        decryption_id: str,
        book: dict,
    ) -> None:
        """
        Execute a single book decryption operation in background.

        This queues and monitors a single book decryption. It:
        1. Converts API dict to operations list format
        2. Updates decryption status to 'decrypting'
        3. Calls decryptor with progress callback
        4. Updates decryption status based on result
        5. Broadcasts decryption events

        Args:
            user_id: User UUID initiating the decryption
            decryption_id: Unique decryption identifier
            book: Book dictionary with {"asin": str, "title": str}

        Raises:
            Logs errors to database instead of raising

        Example:
            # In a router:
            background_tasks.add_task(
                BackgroundTaskService.execute_decrypt_operation,
                user_id=user_id,
                decryption_id=decryption_id,
                book={"asin": "B123456789", "title": "Example Book"}
            )
        """
        asin = None
        try:
            # Convert API format to operations format
            book_list = BackgroundTaskService._dict_to_book_list(book)
            asin = book_list[0]
            title = book_list[1]

            logger.info(
                f"[Decryption {decryption_id}] Starting decryption for {title} ({asin})"
            )

            # Update status to decrypting
            decryption_ops.update_decryption_status(
                decryption_id=decryption_id,
                status="decrypting",
            )

            # Create progress callback
            progress_callback = await BackgroundTaskService._create_progress_callback(
                user_id
            )

            # Execute decryption
            success = await decrypt_book(book_list, progress_callback=progress_callback)

            if success:
                logger.info(f"[Decryption {decryption_id}] Decryption completed successfully")

                # Update status to completed
                decryption_ops.update_decryption_status(
                    decryption_id=decryption_id,
                    status="completed",
                )

                # Broadcast completion event
                await ws_manager.broadcast_to_user(
                    user_id=user_id,
                    event_type=EventType.DECRYPT_COMPLETED.value,
                    data={
                        "decryption_id": decryption_id,
                        "asin": asin,
                        "title": title,
                        "status": "completed",
                        "timestamp": datetime.now(timezone.utc).timestamp(),
                    },
                )
            else:
                logger.warning(f"[Decryption {decryption_id}] Decryption failed")

                # Update status to failed
                decryption_ops.update_decryption_status(
                    decryption_id=decryption_id,
                    status="failed",
                    error_message="Decryption operation returned false",
                )

                # Broadcast failure event
                await ws_manager.broadcast_to_user(
                    user_id=user_id,
                    event_type=EventType.DECRYPT_FAILED.value,
                    data={
                        "decryption_id": decryption_id,
                        "asin": asin,
                        "title": title,
                        "error": "Decryption operation failed",
                        "timestamp": datetime.now(timezone.utc).timestamp(),
                    },
                )

        except ValueError as e:
            # Parameter validation error
            logger.error(f"[Decryption {decryption_id}] Invalid parameters: {e}")

            decryption_ops.update_decryption_status(
                decryption_id=decryption_id,
                status="failed",
                error_message=f"Invalid book parameters: {str(e)}",
            )

            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.DECRYPT_FAILED.value,
                data={
                    "decryption_id": decryption_id,
                    "asin": asin,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                },
            )

        except Exception as e:
            logger.error(
                f"[Decryption {decryption_id}] Unexpected error: {e}",
                exc_info=True,
            )

            # Update status to failed
            decryption_ops.update_decryption_status(
                decryption_id=decryption_id,
                status="failed",
                error_message=str(e),
            )

            # Log error
            try:
                error_ops.log_error(
                    error_type="decryption_error",
                    error_message=str(e),
                    user_id=user_id,
                    asin=asin,
                    severity="error",
                    context={"decryption_id": decryption_id},
                )
            except Exception as log_err:
                logger.error(f"Failed to log decryption error: {log_err}")

            # Broadcast failure
            await ws_manager.broadcast_to_user(
                user_id=user_id,
                event_type=EventType.DECRYPT_FAILED.value,
                data={
                    "decryption_id": decryption_id,
                    "asin": asin,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).timestamp(),
                },
            )


# Singleton instance
background_task_service = BackgroundTaskService()
