"""Book database operations."""

from typing import Dict, List, Optional

from loguru import logger

from .db_pool import DatabasePool  # noqa: F401
from .db_pool import db_pool as _db_pool


class BookOperations:
    """Database operations for book management."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def add_book(
        self,
        asin: str,
        user_id: str,
        title: str,
        purchase_date: Optional[str] = None,
        runtime_min: Optional[int] = None,
        author: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Add a new book to the library.

        Args:
            asin: Amazon Standard Identification Number
            user_id: User UUID
            title: Book title
            purchase_date: Purchase date (YYYY-MM-DD)
            runtime_min: Runtime in minutes
            author: Author name
            **kwargs: Additional metadata (narrator, series_name, description, rating)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO books (
                        asin, user_id, title, purchase_date, runtime_min, author,
                        narrator, series_name, description, rating
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asin) DO UPDATE SET
                        title = EXCLUDED.title,
                        purchase_date = EXCLUDED.purchase_date,
                        runtime_min = EXCLUDED.runtime_min,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        asin,
                        user_id,
                        title,
                        purchase_date,
                        runtime_min,
                        author,
                        kwargs.get("narrator"),
                        kwargs.get("series_name"),
                        kwargs.get("description"),
                        kwargs.get("rating"),
                    ),
                )
                logger.info(f"Added/updated book: {title} (ASIN: {asin})")
                return True
        except Exception as e:
            logger.error(f"Failed to add book: {e}")
            return False

    def remove_book(self, asin: str) -> bool:
        """
        Remove a book from the library.

        Args:
            asin: Amazon Standard Identification Number

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute("DELETE FROM books WHERE asin = %s", (asin,))
                logger.info(f"Removed book: {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove book: {e}")
            return False

    def get_user_books(self, user_id: str) -> List[Dict]:
        """
        Get all books for a user.

        Args:
            user_id: User's UUID

        Returns:
            List of book dicts
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM v_books_complete
                    WHERE user_id = %s
                    ORDER BY purchase_date DESC
                """,
                    (user_id,),
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get user books: {e}")
            return []

    def get_book_by_asin(self, asin: str) -> Optional[Dict]:
        """
        Get book details by ASIN.

        Args:
            asin: Amazon Standard Identification Number

        Returns:
            Book dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM v_books_complete WHERE asin = %s",
                    (asin,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get book: {e}")
            return None


# Singleton instance
book_ops = BookOperations()
