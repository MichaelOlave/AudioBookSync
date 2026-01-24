"""Book processing handler orchestrating download and decrypt workflows."""

from typing import Any, Awaitable, Callable, Optional

from loguru import logger

from ...database.engine import AsyncSessionLocal
from ...database.services import user_service
from ...domain.progress import safe_progress_callback
from ..decryptor import decrypt_book
from ..downloader import download_book


class BookProcessingHandler:
    """Handles the complete book processing workflow.

    This handler encapsulates the logic for processing a single book,
    which involves downloading and decrypting it with progress tracking.

    Previously, this logic was scattered across the process_book() function
    in library_sync.py with 8 responsibilities and 97 lines of code.

    Now it's organized into focused methods with clear separation of concerns:
    - process_book(): Main orchestration entry point
    - _execute_download_phase(): Handle download with progress tracking
    - _execute_decrypt_phase(): Handle decryption with progress tracking
    - _handle_processing_failure(): Centralized error handling
    """

    async def process_book(
        self,
        user_id: str,
        book: dict,
        library_manager,
        progress_callback: Optional[Callable[..., Awaitable[Any]]] = None,
    ) -> bool:
        """Process a single book: download and decrypt.

        Args:
            user_id: User ID for context
            book: Book dictionary with 'asin' and 'title' keys
            library_manager: LibraryManager instance for error logging
            progress_callback: Optional async callable for progress updates

        Returns:
            True if successful, False otherwise
        """
        asin = book.get("asin")
        title = book.get("title")

        if not asin or not title:
            logger.error("Book must have asin and title")
            return False

        try:
            logger.info(f"Processing book: {title}")

            # Download phase
            download_success = await self._execute_download_phase(
                user_id, asin, title, progress_callback
            )
            if not download_success:
                await self._handle_processing_failure(
                    asin, title, library_manager, progress_callback, "Download failed"
                )
                return False

            # Decrypt phase
            decrypt_success = await self._execute_decrypt_phase(
                user_id, asin, title, progress_callback
            )
            if not decrypt_success:
                await self._handle_processing_failure(
                    asin, title, library_manager, progress_callback, "Decryption failed"
                )
                return False

            logger.info(f"Successfully processed: {title}")
            return True

        except Exception as e:
            await self._handle_processing_failure(
                asin, title, library_manager, progress_callback, str(e)
            )
            return False

    async def _execute_download_phase(
        self,
        user_id: str,
        asin: str,
        title: str,
        progress_callback: Optional[Callable[..., Awaitable[Any]]] = None,
    ) -> bool:
        """Execute download phase with progress tracking.

        Args:
            user_id: User ID for context
            asin: Book ASIN
            title: Book title
            progress_callback: Optional progress callback

        Returns:
            True if download successful, False otherwise
        """
        await safe_progress_callback(
            progress_callback,
            event_type="download.started",
            asin=asin,
            title=title,
        )

        async with AsyncSessionLocal() as db:
            audible_auth = await user_service.get_audible_auth_json(
                db,
                user_id,
                redact_secrets=False,
            )
            user = await user_service.get_user_by_id(db, user_id)
            activation_bytes = (
                str(user.activation_bytes) if user and user.activation_bytes else None
            )

        if not audible_auth:
            logger.error("Audible credentials not configured for user")
            return False
        if not activation_bytes:
            logger.error("Activation bytes not configured for user")
            return False

        success = await download_book(
            [asin, title],
            user_id=user_id,
            progress_callback=progress_callback,
            audible_auth=audible_auth,
            activation_bytes=activation_bytes,
        )

        if success:
            await safe_progress_callback(
                progress_callback,
                event_type="download.completed",
                asin=asin,
                title=title,
            )

        return success

    async def _execute_decrypt_phase(
        self,
        user_id: str,
        asin: str,
        title: str,
        progress_callback: Optional[Callable[..., Awaitable[Any]]] = None,
    ) -> bool:
        """Execute decrypt phase with progress tracking.

        Args:
            user_id: User ID for context
            asin: Book ASIN
            title: Book title
            progress_callback: Optional progress callback

        Returns:
            True if decryption successful, False otherwise
        """
        await safe_progress_callback(
            progress_callback,
            event_type="decrypt.started",
            asin=asin,
            title=title,
        )

        async with AsyncSessionLocal() as db:
            user = await user_service.get_user_by_id(db, user_id)
            activation_bytes = (
                str(user.activation_bytes) if user and user.activation_bytes else None
            )

        if not activation_bytes:
            logger.error("Activation bytes not configured for user")
            return False

        success = await decrypt_book(
            [asin, title],
            user_id=user_id,
            progress_callback=progress_callback,
            activation_bytes=activation_bytes,
        )

        if success:
            await safe_progress_callback(
                progress_callback,
                event_type="decrypt.completed",
                asin=asin,
                title=title,
            )

        return success

    async def _handle_processing_failure(
        self,
        asin: str,
        title: str,
        library_manager,
        progress_callback: Optional[Callable[..., Awaitable[Any]]],
        error_message: str,
    ) -> None:
        """Handle processing failure with logging and callbacks.

        Args:
            asin: Book ASIN
            title: Book title
            library_manager: LibraryManager for error logging
            progress_callback: Optional progress callback
            error_message: Error message to log
        """
        logger.error(f"Processing failed for {title}: {error_message}")

        # Broadcast error event
        await safe_progress_callback(
            progress_callback,
            event_type="sync.error",
            asin=asin,
            title=title,
            error=error_message,
        )

        # Log error to database
        if library_manager:
            try:
                await library_manager.log_error(
                    error_type="sync_error",
                    error_message=f"Failed to process book: {error_message}",
                    asin=asin,
                    severity="error",
                )
            except Exception as e:
                logger.warning(f"Failed to log error to database: {e}")


# Singleton instance
book_processor = BookProcessingHandler()
