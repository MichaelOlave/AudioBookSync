"""Database operations for book availability and licensing information."""

from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from .db_pool import db_pool as _db_pool


class BookAvailabilityOperations:
    """Database operations for book availability and user rights."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_availability(
        self,
        asin: str,
        is_playable: bool = True,
        is_returnable: bool = True,
        is_removable: bool = True,
        is_downloadable: bool = True,
        is_archived: bool = False,
    ) -> bool:
        """
        Create availability record for a book (auto-created via trigger, but can be explicit).

        Args:
            asin: Book's ASIN
            is_playable: Can the user play this?
            is_returnable: Can be returned?
            is_removable: Can be removed from library?
            is_downloadable: Can be downloaded?
            is_archived: Is archived?

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO book_availability (
                        asin, is_playable, is_returnable, is_removable,
                        is_downloadable, is_archived
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asin) DO NOTHING
                    """,
                    (
                        asin,
                        is_playable,
                        is_returnable,
                        is_removable,
                        is_downloadable,
                        is_archived,
                    ),
                )
                logger.debug(f"Created availability record for book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to create availability record: {e}")
            return False

    def get_availability(self, asin: str) -> Optional[Dict]:
        """
        Get availability information for a book.

        Args:
            asin: Book's ASIN

        Returns:
            Availability dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM book_availability WHERE asin = %s",
                    (asin,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get availability: {e}")
            return None

    def update_playable(self, asin: str, is_playable: bool) -> bool:
        """
        Update playable status for a book.

        Args:
            asin: Book's ASIN
            is_playable: New playable status

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE book_availability SET is_playable = %s WHERE asin = %s",
                    (is_playable, asin),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update playable status: {e}")
            return False

    def update_returnable(self, asin: str, is_returnable: bool) -> bool:
        """
        Update returnable status for a book.

        Args:
            asin: Book's ASIN
            is_returnable: New returnable status

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE book_availability SET is_returnable = %s WHERE asin = %s",
                    (is_returnable, asin),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update returnable status: {e}")
            return False

    def update_removable(self, asin: str, is_removable: bool) -> bool:
        """
        Update removable status for a book.

        Args:
            asin: Book's ASIN
            is_removable: New removable status

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE book_availability SET is_removable = %s WHERE asin = %s",
                    (is_removable, asin),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update removable status: {e}")
            return False

    def update_archived(self, asin: str, is_archived: bool) -> bool:
        """
        Update archived status for a book.

        Args:
            asin: Book's ASIN
            is_archived: New archived status

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE book_availability SET is_archived = %s WHERE asin = %s",
                    (is_archived, asin),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update archived status: {e}")
            return False

    def set_license_status(
        self,
        asin: str,
        status: str,
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """
        Set license status and expiration for a book.

        Args:
            asin: Book's ASIN
            status: License status (active, expired, revoked, etc.)
            expires_at: License expiration date

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE book_availability
                    SET license_status = %s, expires_at = %s
                    WHERE asin = %s
                    """,
                    (status, expires_at, asin),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to set license status: {e}")
            return False

    def get_expiring_licenses(self, days_until_expiry: int = 30) -> list:
        """
        Get books with licenses expiring within specified days.

        Args:
            days_until_expiry: Number of days to look ahead

        Returns:
            List of availability dicts
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM book_availability
                    WHERE expires_at IS NOT NULL
                    AND expires_at <= CURRENT_TIMESTAMP + INTERVAL '%s days'
                    AND license_status != 'expired'
                    ORDER BY expires_at ASC
                    """,
                    (days_until_expiry,),
                )
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Failed to get expiring licenses: {e}")
            return []


# Singleton instance
book_availability_ops = BookAvailabilityOperations()
