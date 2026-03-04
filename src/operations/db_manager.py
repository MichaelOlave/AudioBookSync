"""Database operations manager for library management (replaces CSV).

This module provides async ORM-backed library management replacing csv_manager.py.
It uses the ORM services for all operations.
"""

from typing import Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.services import book_service, error_service, sync_service


class LibraryManager:
    """Async ORM-backed library manager for Audible books."""

    def __init__(self, db: AsyncSession, user_id: str):
        """Initialize library manager for a specific user.

        Args:
            db: AsyncSession database connection
            user_id: UUID of the user
        """
        self.db = db
        self.user_id = user_id

    async def add_book(
        self,
        asin: str,
        title: str,
        purchase_date: Optional[str] = None,
        runtime_min: Optional[int] = None,
        author: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Add a book to the user's library.

        Args:
            asin: Amazon Standard Identification Number
            title: Book title
            purchase_date: Purchase date (YYYY-MM-DD)
            runtime_min: Runtime in minutes
            author: Author name
            **kwargs: Additional metadata (narrator, series_name, description, rating)

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await book_service.add_book(
                db=self.db,
                asin=asin,
                user_id=self.user_id,
                title=title,
                purchase_date=purchase_date,
                runtime_min=runtime_min,
                author=author,
                **kwargs,
            )
            if success:
                logger.info(f"Added book to library: {title} (ASIN: {asin})")
            return success
        except Exception as e:
            logger.error(f"Failed to add book {asin}: {e}")
            return False

    async def add_book_with_metadata(
        self,
        asin: str,
        title: str,
        book_data: Dict,
        purchase_date: Optional[str] = None,
    ) -> bool:
        """Add a book with comprehensive metadata from Audible API.

        This method integrates full metadata from the Audible API response,
        populating all 7 metadata tables (contributors, media_info, reading_progress,
        book_availability, companion_materials, book_metadata_json).

        Args:
            asin: Amazon Standard Identification Number
            title: Book title
            book_data: Complete Audible API response with all response groups
            purchase_date: Purchase date (YYYY-MM-DD)

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await book_service.add_book_with_metadata(
                db=self.db,
                asin=asin,
                user_id=self.user_id,
                title=title,
                book_data=book_data,
                purchase_date=purchase_date,
            )
            if success:
                logger.info(f"Added book with comprehensive metadata: {title} (ASIN: {asin})")
            return success
        except Exception as e:
            logger.error(f"Failed to add book with metadata {asin}: {e}")
            return False

    async def remove_book(self, asin: str) -> bool:
        """Remove a book from the user's library.

        Args:
            asin: Amazon Standard Identification Number

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await book_service.delete_book(
                db=self.db,
                asin=asin,
                user_id=self.user_id,
            )
            if success:
                logger.info(f"Removed book from library: {asin}")
            return success
        except Exception as e:
            logger.error(f"Failed to remove book {asin}: {e}")
            return False

    async def get_user_books(self) -> List[Dict]:
        """Get all books for the user.

        Returns:
            List of book dictionaries (ORM objects converted to dicts)
        """
        try:
            books = await book_service.get_books_by_user(db=self.db, user_id=self.user_id)
            logger.info(f"Retrieved {len(books)} books for user")
            return books
        except Exception as e:
            logger.error(f"Failed to get user books: {e}")
            return []

    async def get_missing_books(self) -> List[Dict]:
        """Get books from Audible that aren't in local library.

        This should be called after comparing with Audible library.
        For now, returns books not yet downloaded.

        Returns:
            List of book dictionaries representing missing books
        """
        try:
            # Get all user books
            all_books = await self.get_user_books()

            # Filter to books not yet downloaded
            missing = [book for book in all_books if not book.get("is_downloaded")]

            logger.info(f"Found {len(missing)} books to download")
            return missing
        except Exception as e:
            logger.error(f"Failed to get missing books: {e}")
            return []

    async def book_exists(self, asin: str) -> bool:
        """Check if a book exists in the user's library.

        Args:
            asin: Amazon Standard Identification Number

        Returns:
            True if book exists, False otherwise
        """
        try:
            user_book = await book_service.get_user_book(
                db=self.db,
                user_id=self.user_id,
                asin=asin,
            )
            return user_book is not None
        except Exception as e:
            logger.error(f"Failed to check if book exists: {e}")
            return False

    async def create_sync(self, sync_type: str = "full") -> Optional[str]:
        """Create a new sync operation record.

        Args:
            sync_type: Type of sync (full, incremental, manual)

        Returns:
            sync_id if successful, None otherwise
        """
        try:
            sync_history = await sync_service.create_sync_history(
                db=self.db,
                user_id=UUID(self.user_id),
                sync_type=sync_type,
            )
            if sync_history:
                sync_id = str(sync_history.sync_id)
                logger.info(f"Created sync record: {sync_id}")
                return sync_id
            return None
        except Exception as e:
            logger.error(f"Failed to create sync: {e}")
            return None

    async def complete_sync(
        self,
        sync_id: str,
        status: str = "completed",
        books_found: int = 0,
        books_added: int = 0,
        books_downloaded: int = 0,
        books_decrypted: int = 0,
        errors_count: int = 0,
    ) -> bool:
        """Complete a sync operation.

        Args:
            sync_id: Sync operation ID
            status: Final status (completed, partial, failed)
            books_found: Number of books found in library
            books_added: Number of books added
            books_downloaded: Number of books downloaded
            books_decrypted: Number of books decrypted
            errors_count: Number of errors encountered

        Returns:
            True if successful, False otherwise
        """
        try:
            success = await sync_service.update_sync_status(
                db=self.db,
                sync_id=UUID(sync_id),
                status=status,
                books_found=books_found,
                books_added=books_added,
                books_downloaded=books_downloaded,
                books_decrypted=books_decrypted,
                errors_count=errors_count,
            )
            if success:
                logger.info(f"Completed sync {sync_id} with status {status}")
            return success
        except Exception as e:
            logger.error(f"Failed to complete sync: {e}")
            return False

    async def log_error(
        self,
        error_type: str,
        error_message: str,
        asin: Optional[str] = None,
        severity: str = "error",
        **kwargs,
    ) -> bool:
        """Log an error during sync.

        Args:
            error_type: Type of error (download_error, decryption_error, etc.)
            error_message: Error description
            asin: Associated book ASIN (optional)
            severity: Error severity (info, warning, error, critical)
            **kwargs: Additional data (stack_trace, context, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            error_log = await error_service.log_error(
                db=self.db,
                error_type=error_type,
                error_message=error_message,
                user_id=UUID(self.user_id),
                asin=asin,
                severity=severity,
                error_details=kwargs,
            )
            return error_log is not None
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
            return False


# Factory function for convenience
async def get_library_manager(db: AsyncSession, user_id: str) -> LibraryManager:
    """Get a library manager instance for a user.

    Args:
        db: AsyncSession database connection
        user_id: UUID of the user

    Returns:
        LibraryManager instance
    """
    return LibraryManager(db=db, user_id=user_id)
