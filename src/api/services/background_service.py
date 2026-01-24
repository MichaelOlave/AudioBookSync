"""Background task service for orchestrating operations in background threads.

This service bridges the API layer (which uses dictionaries) with the operations layer
(which expects lists and specific formats). It handles:
- Parameter conversion between API and operations formats
- User context injection for all operations
- WebSocket progress event broadcasting
- Error handling and logging
"""

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from loguru import logger

from ...database.engine import AsyncSessionLocal
from ...database.services import (
    decryption_service,
    download_service,
    error_service,
    user_service,
)
from ...operations.decryptor import decrypt_book
from ...operations.downloader import download_book
from ...operations.library_sync import sync_library
from ..websockets import EventType, ws_manager
from .sync_service import SyncService

# ===========================================
# Operation Executor Pattern (Template Method)
# ===========================================


class OperationExecutor:
    """Base executor for download/decrypt operations using Template Method pattern.

    This base class eliminates 160+ lines of duplication by defining the common
    workflow for executing operations (download, decrypt) while allowing subclasses
    to specialize specific behaviors.

    The pattern works by having all orchestration logic here and subclasses override
    just the operation-specific methods (_execute_operation, _update_status, etc).
    """

    def __init__(
        self,
        user_id: str,
        operation_id: str,
        book: dict,
        operation_type: str,  # "download" or "decrypt"
    ):
        self.user_id = user_id
        self.operation_id = operation_id
        self.book = book
        self.operation_type = operation_type
        self.asin = None
        self.title = None

    async def _create_progress_callback(self) -> Callable:
        """Create a progress callback for this operation."""
        return await BackgroundTaskService._create_progress_callback(self.user_id)

    async def execute(self) -> None:
        """Template method that orchestrates operation execution.

        This method defines the algorithm structure. Subclasses override
        specific steps (_execute_operation, etc) to customize behavior.
        """
        try:
            # Convert API format to operations format
            book_list = BackgroundTaskService._dict_to_book_list(self.book)
            self.asin = book_list[0]
            self.title = book_list[1]

            logger.info(
                f"[{self.operation_type.capitalize()} {self.operation_id}] "
                f"Starting {self.operation_type} for {self.title} ({self.asin})"
            )

            # Update status to in-progress
            await self._update_status("in_progress")

            # Create progress callback
            progress_callback = await self._create_progress_callback()

            # Execute the actual operation (subclass-specific)
            success = await self._execute_operation(book_list, progress_callback)

            if success:
                await self._handle_success()
            else:
                await self._handle_failure("Operation returned false")

        except ValueError as e:
            await self._handle_validation_error(e)
        except Exception as e:
            await self._handle_unexpected_error(e)

    async def _execute_operation(self, book_list: list, progress_callback) -> bool:
        """Execute the actual operation. Override in subclass."""
        raise NotImplementedError

    async def _update_status(self, status: str, **kwargs) -> None:
        """Update operation status in database. Override in subclass."""
        raise NotImplementedError

    async def _handle_success(self) -> None:
        """Handle successful operation."""
        logger.info(
            f"[{self.operation_type.capitalize()} {self.operation_id}] "
            f"Operation completed successfully"
        )

        await self._update_status("completed")

        await self._broadcast_event(
            f"{self.operation_type}.completed",
            {
                f"{self.operation_type}_id": self.operation_id,
                "asin": self.asin,
                "title": self.title,
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).timestamp(),
            },
        )

    async def _handle_failure(self, error: str) -> None:
        """Handle failed operation."""
        logger.warning(
            f"[{self.operation_type.capitalize()} {self.operation_id}] " f"Operation failed"
        )

        await self._update_status(
            "failed",
            error_message=error,
        )

        await self._broadcast_event(
            f"{self.operation_type}.failed",
            {
                f"{self.operation_type}_id": self.operation_id,
                "asin": self.asin,
                "title": self.title,
                "error": error,
                "timestamp": datetime.now(timezone.utc).timestamp(),
            },
        )

    async def _handle_validation_error(self, error: ValueError) -> None:
        """Handle validation errors."""
        logger.error(
            f"[{self.operation_type.capitalize()} {self.operation_id}] "
            f"Invalid parameters: {error}"
        )

        await self._update_status(
            "failed",
            error_message=f"Invalid book parameters: {str(error)}",
        )

        await self._broadcast_event(
            f"{self.operation_type}.failed",
            {
                f"{self.operation_type}_id": self.operation_id,
                "asin": self.asin,
                "error": str(error),
                "timestamp": datetime.now(timezone.utc).timestamp(),
            },
        )

    async def _handle_unexpected_error(self, error: Exception) -> None:
        """Handle unexpected errors."""
        logger.error(
            f"[{self.operation_type.capitalize()} {self.operation_id}] "
            f"Unexpected error: {error}",
            exc_info=True,
        )

        await self._update_status("failed", error_message=str(error))

        # Log to error table
        try:
            await self._log_error(error)
        except Exception as log_err:
            logger.error(f"Failed to log {self.operation_type} error: {log_err}")

        await self._broadcast_event(
            f"{self.operation_type}.failed",
            {
                f"{self.operation_type}_id": self.operation_id,
                "asin": self.asin,
                "error": str(error),
                "timestamp": datetime.now(timezone.utc).timestamp(),
            },
        )

    async def _log_error(self, error: Exception) -> None:
        """Log error to database. Override in subclass if needed."""

    async def _broadcast_event(self, event_type_key: str, data: dict) -> None:
        """Broadcast WebSocket event."""
        # Map event type key to EventType enum value
        event_type_map = {
            "download.started": (
                EventType.DOWNLOAD_STARTED.value
                if hasattr(EventType, "DOWNLOAD_STARTED")
                else "download.started"
            ),
            "download.completed": (
                EventType.DOWNLOAD_COMPLETED.value
                if hasattr(EventType, "DOWNLOAD_COMPLETED")
                else "download.completed"
            ),
            "download.failed": (
                EventType.DOWNLOAD_FAILED.value
                if hasattr(EventType, "DOWNLOAD_FAILED")
                else "download.failed"
            ),
            "decrypt.started": (
                EventType.DECRYPT_STARTED.value
                if hasattr(EventType, "DECRYPT_STARTED")
                else "decrypt.started"
            ),
            "decrypt.completed": (
                EventType.DECRYPT_COMPLETED.value
                if hasattr(EventType, "DECRYPT_COMPLETED")
                else "decrypt.completed"
            ),
            "decrypt.failed": (
                EventType.DECRYPT_FAILED.value
                if hasattr(EventType, "DECRYPT_FAILED")
                else "decrypt.failed"
            ),
        }

        event_type_value = event_type_map.get(event_type_key, event_type_key)

        await ws_manager.broadcast_to_user(
            user_id=self.user_id,
            event_type=event_type_value,
            data=data,
        )


class DownloadExecutor(OperationExecutor):
    """Specialized executor for download operations."""

    def __init__(self, user_id: str, download_id: str, book: dict):
        super().__init__(user_id, download_id, book, "download")

    async def _create_progress_callback(self) -> Callable:
        """Create a progress callback that persists download size."""
        base_callback = await BackgroundTaskService._create_progress_callback(self.user_id)
        last_persisted_bytes = 0

        async def progress_callback(event_type: str, **data: Any) -> None:
            nonlocal last_persisted_bytes
            if event_type == "download.progress":
                bytes_downloaded = data.get("bytes_downloaded")
                if isinstance(bytes_downloaded, (int, float)):
                    new_size = int(bytes_downloaded)
                    if new_size > 0 and new_size != last_persisted_bytes:
                        last_persisted_bytes = new_size
                        try:
                            async with AsyncSessionLocal() as db:
                                download = await download_service.get_download_by_id(
                                    db, UUID(self.operation_id)
                                )
                                if download:
                                    download.file_size_bytes = new_size
                                    await db.commit()
                        except Exception as e:
                            logger.warning(
                                f"Failed to persist download size for {self.operation_id}: {e}"
                            )

            await base_callback(event_type, **data)

        return progress_callback

    async def _execute_operation(self, book_list: list, progress_callback) -> bool:
        """Execute download operation."""
        async with AsyncSessionLocal() as db:
            audible_auth = await user_service.get_audible_auth_json(
                db,
                self.user_id,
                redact_secrets=False,
            )
            user = await user_service.get_user_by_id(db, self.user_id)
            activation_bytes = user.activation_bytes if user else None

        if not audible_auth:
            raise ValueError("Audible credentials not configured for user")
        if not activation_bytes:
            raise ValueError("Activation bytes not configured for user")

        return await download_book(
            book_list,
            user_id=self.user_id,
            progress_callback=progress_callback,
            audible_auth=audible_auth,
            activation_bytes=activation_bytes,
        )

    async def _update_status(self, status: str, **kwargs) -> None:
        """Update download status in database using ORM."""
        try:
            async with AsyncSessionLocal() as db:
                await download_service.update_download_status(
                    db=db,
                    entity_id=UUID(self.operation_id),
                    status=status,
                    **kwargs,
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update download status: {e}")

    async def _log_error(self, error: Exception) -> None:
        """Log download error to database using ORM."""
        try:
            async with AsyncSessionLocal() as db:
                await error_service.log_error(
                    db=db,
                    error_type="download_error",
                    error_message=str(error),
                    user_id=UUID(self.user_id),
                    asin=self.asin,
                    severity="error",
                    error_details={"download_id": self.operation_id},
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to log download error: {e}")


class DecryptExecutor(OperationExecutor):
    """Specialized executor for decrypt operations."""

    def __init__(self, user_id: str, decryption_id: str, book: dict):
        super().__init__(user_id, decryption_id, book, "decrypt")

    async def _execute_operation(self, book_list: list, progress_callback) -> bool:
        """Execute decrypt operation."""
        async with AsyncSessionLocal() as db:
            user = await user_service.get_user_by_id(db, self.user_id)
            activation_bytes = user.activation_bytes if user else None

        if not activation_bytes:
            raise ValueError("Activation bytes not configured for user")

        return await decrypt_book(
            book_list,
            user_id=self.user_id,
            progress_callback=progress_callback,
            activation_bytes=activation_bytes,
        )

    async def _update_status(self, status: str, **kwargs) -> None:
        """Update decryption status in database using ORM."""
        try:
            async with AsyncSessionLocal() as db:
                await decryption_service.update_decryption_status(
                    db=db,
                    entity_id=UUID(self.operation_id),
                    status=status,
                    **kwargs,
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update decryption status: {e}")

    async def _log_error(self, error: Exception) -> None:
        """Log decryption error to database using ORM."""
        try:
            async with AsyncSessionLocal() as db:
                await error_service.log_error(
                    db=db,
                    error_type="decryption_error",
                    error_message=str(error),
                    user_id=UUID(self.user_id),
                    asin=self.asin,
                    severity="error",
                    error_details={"decryption_id": self.operation_id},
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to log decryption error: {e}")


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
                    data["timestamp"] = datetime.now(timezone.utc).timestamp()

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
            progress_callback = await BackgroundTaskService._create_progress_callback(user_id)

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

            # Log error to database using ORM
            try:
                async with AsyncSessionLocal() as db:
                    await error_service.log_error(
                        db=db,
                        error_type="sync_error",
                        error_message=str(e),
                        user_id=UUID(user_id),
                        sync_id=UUID(sync_id),
                        severity="error",
                        error_details={"sync_type": sync_type},
                    )
                    await db.commit()
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
        """Execute a single book download operation in background.

        Delegates to DownloadExecutor which uses the Template Method pattern
        to orchestrate the download with progress tracking, status updates,
        error handling, and WebSocket broadcasting.

        Args:
            user_id: User UUID initiating the download
            download_id: Unique download identifier
            book: Book dictionary with {"asin": str, "title": str}

        Example:
            background_tasks.add_task(
                BackgroundTaskService.execute_download_operation,
                user_id=user_id,
                download_id=download_id,
                book={"asin": "B123456789", "title": "Example Book"}
            )
        """
        executor = DownloadExecutor(user_id, download_id, book)
        await executor.execute()

    @staticmethod
    async def execute_decrypt_operation(
        user_id: str,
        decryption_id: str,
        book: dict,
    ) -> None:
        """Execute a single book decryption operation in background.

        Delegates to DecryptExecutor which uses the Template Method pattern
        to orchestrate the decryption with progress tracking, status updates,
        error handling, and WebSocket broadcasting.

        Args:
            user_id: User UUID initiating the decryption
            decryption_id: Unique decryption identifier
            book: Book dictionary with {"asin": str, "title": str}

        Example:
            background_tasks.add_task(
                BackgroundTaskService.execute_decrypt_operation,
                user_id=user_id,
                decryption_id=decryption_id,
                book={"asin": "B123456789", "title": "Example Book"}
            )
        """
        executor = DecryptExecutor(user_id, decryption_id, book)
        await executor.execute()


# Singleton instance
background_task_service = BackgroundTaskService()
