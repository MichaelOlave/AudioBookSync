"""Database operations for user reading progress tracking."""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from .db_pool import db_pool as _db_pool


class ReadingProgressOperations:
    """Database operations for tracking user reading progress."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_progress(
        self,
        asin: str,
        user_id: str,
        percent_complete: int = 0,
        position_ms: int = 0,
    ) -> bool:
        """
        Create a reading progress record for a user and book.

        Args:
            asin: Book's ASIN
            user_id: User's UUID
            percent_complete: Initial completion percentage (0-100)
            position_ms: Initial position in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO reading_progress (asin, user_id, percent_complete, position_ms)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (asin, user_id) DO NOTHING
                    """,
                    (asin, user_id, percent_complete, position_ms),
                )
                logger.debug(f"Created progress record for {user_id} on book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to create progress record: {e}")
            return False

    def get_progress(self, asin: str, user_id: str) -> Optional[Dict]:
        """
        Get reading progress for a user and book.

        Args:
            asin: Book's ASIN
            user_id: User's UUID

        Returns:
            Progress dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM reading_progress WHERE asin = %s AND user_id = %s",
                    (asin, user_id),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get progress: {e}")
            return None

    def update_progress(
        self,
        asin: str,
        user_id: str,
        percent_complete: Optional[int] = None,
        position_ms: Optional[int] = None,
    ) -> bool:
        """
        Update reading progress for a user and book.

        Args:
            asin: Book's ASIN
            user_id: User's UUID
            percent_complete: Completion percentage (0-100)
            position_ms: Current position in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                updates = []
                values = []

                if percent_complete is not None:
                    updates.append("percent_complete = %s")
                    values.append(percent_complete)

                if position_ms is not None:
                    updates.append("position_ms = %s")
                    values.append(position_ms)

                if not updates:
                    return True

                updates.append("last_position_update = CURRENT_TIMESTAMP")
                values.extend([asin, user_id])

                query = f"""
                    UPDATE reading_progress
                    SET {', '.join(updates)}
                    WHERE asin = %s AND user_id = %s
                """
                cursor.execute(query, values)
                logger.debug(f"Updated progress for {user_id} on book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
            return False

    def mark_as_finished(
        self, asin: str, user_id: str, date_finished: Optional[datetime] = None
    ) -> bool:
        """
        Mark a book as finished for a user.

        Args:
            asin: Book's ASIN
            user_id: User's UUID
            date_finished: Date finished (defaults to now)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                if date_finished is None:
                    date_finished = datetime.utcnow()

                cursor.execute(
                    """
                    UPDATE reading_progress
                    SET is_finished = true, percent_complete = 100,
                        date_finished = %s, last_position_update = CURRENT_TIMESTAMP
                    WHERE asin = %s AND user_id = %s
                    """,
                    (date_finished, asin, user_id),
                )
                logger.info(f"Marked book {asin} as finished for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to mark as finished: {e}")
            return False

    def get_user_reading_stats(self, user_id: str) -> Optional[Dict]:
        """
        Get reading statistics for a user using the v_reading_statistics view.

        Args:
            user_id: User's UUID

        Returns:
            Statistics dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM v_reading_statistics WHERE user_id = %s",
                    (user_id,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get reading stats: {e}")
            return None

    def get_in_progress_books(self, user_id: str) -> List[Dict]:
        """
        Get all books currently being read by a user.

        Args:
            user_id: User's UUID

        Returns:
            List of book dicts with progress information
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT b.*, rp.percent_complete, rp.position_ms, rp.is_finished
                    FROM reading_progress rp
                    JOIN books b ON rp.asin = b.asin
                    WHERE rp.user_id = %s AND rp.percent_complete > 0 AND rp.percent_complete < 100
                    ORDER BY rp.last_position_update DESC
                    """,
                    (user_id,),
                )
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Failed to get in-progress books: {e}")
            return []

    def get_finished_books(
        self, user_id: str, limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all books finished by a user.

        Args:
            user_id: User's UUID
            limit: Maximum number of results

        Returns:
            List of book dicts with progress information
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                query = """
                    SELECT b.*, rp.date_finished
                    FROM reading_progress rp
                    JOIN books b ON rp.asin = b.asin
                    WHERE rp.user_id = %s AND rp.is_finished = true
                    ORDER BY rp.date_finished DESC
                """
                if limit:
                    query += f" LIMIT {limit}"

                cursor.execute(query, (user_id,))
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Failed to get finished books: {e}")
            return []


# Singleton instance
reading_progress_ops = ReadingProgressOperations()
