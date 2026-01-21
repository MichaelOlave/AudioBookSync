"""Sync history database operations."""

from typing import Dict, List, Optional

from loguru import logger

from .db_pool import DatabasePool  # noqa: F401
from .db_pool import db_pool as _db_pool


class SyncOperations:
    """Database operations for sync history tracking."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_sync_history(self, user_id: str, sync_type: str = "full") -> Optional[str]:
        """
        Create a sync history entry.

        Args:
            user_id: User's UUID
            sync_type: Type of sync (full, incremental, manual)

        Returns:
            sync_id if successful, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sync_history (user_id, sync_type, status)
                    VALUES (%s, %s, 'in_progress')
                    RETURNING sync_id
                """,
                    (user_id, sync_type),
                )
                result = cursor.fetchone()
                sync_id = str(result["sync_id"]) if result else None
                logger.info(f"Created sync history: {sync_id}")
                return sync_id
        except Exception as e:
            logger.error(f"Failed to create sync history: {e}")
            return None

    def complete_sync_history(
        self,
        sync_id: str,
        status: str,
        books_found: int = 0,
        books_added: int = 0,
        books_downloaded: int = 0,
        books_decrypted: int = 0,
        errors_count: int = 0,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Complete a sync history entry.

        Args:
            sync_id: Sync history UUID
            status: Final status (completed, partial, failed)
            books_found: Number of books found in library
            books_added: Number of books added
            books_downloaded: Number of books downloaded
            books_decrypted: Number of books decrypted
            errors_count: Number of errors encountered
            notes: Additional notes about the sync

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE sync_history
                    SET status = %s,
                        sync_completed_at = CURRENT_TIMESTAMP,
                        duration_seconds = EXTRACT(
                            EPOCH FROM (CURRENT_TIMESTAMP - sync_started_at)
                        ),
                        books_found = %s,
                        books_added = %s,
                        books_downloaded = %s,
                        books_decrypted = %s,
                        errors_count = %s,
                        notes = %s
                    WHERE sync_id = %s
                """,
                    (
                        status,
                        books_found,
                        books_added,
                        books_downloaded,
                        books_decrypted,
                        errors_count,
                        notes,
                        sync_id,
                    ),
                )
                logger.info(f"Completed sync history {sync_id} with status {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to complete sync history: {e}")
            return False

    def get_sync_by_id(self, sync_id: str) -> Optional[Dict]:
        """
        Get a specific sync history entry by ID.

        Args:
            sync_id: Sync history UUID

        Returns:
            Dictionary with sync details if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        sync_id,
                        user_id,
                        sync_type,
                        status,
                        sync_started_at,
                        sync_completed_at,
                        duration_seconds,
                        books_found,
                        books_added,
                        books_downloaded,
                        books_decrypted,
                        errors_count,
                        notes,
                        created_at,
                        updated_at
                    FROM sync_history
                    WHERE sync_id = %s
                """,
                    (sync_id,),
                )
                result = cursor.fetchone()
                if result:
                    logger.debug(f"Retrieved sync history: {sync_id}")
                    return dict(result)
                logger.warning(f"Sync history not found: {sync_id}")
                return None
        except Exception as e:
            logger.error(f"Failed to get sync history {sync_id}: {e}")
            return None

    def get_user_sync_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Get sync history for a specific user.

        Args:
            user_id: User's UUID
            limit: Maximum number of records to return (default: 10)

        Returns:
            List of sync history dictionaries, ordered by most recent first
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        sync_id,
                        user_id,
                        sync_type,
                        status,
                        sync_started_at,
                        sync_completed_at,
                        duration_seconds,
                        books_found,
                        books_added,
                        books_downloaded,
                        books_decrypted,
                        errors_count,
                        notes,
                        created_at,
                        updated_at
                    FROM sync_history
                    WHERE user_id = %s
                    ORDER BY sync_started_at DESC
                    LIMIT %s
                """,
                    (user_id, limit),
                )
                results = cursor.fetchall()
                sync_history = [dict(row) for row in results]
                logger.debug(f"Retrieved {len(sync_history)} sync records for user {user_id}")
                return sync_history
        except Exception as e:
            logger.error(f"Failed to get sync history for user {user_id}: {e}")
            return []


# Singleton instance
sync_ops = SyncOperations()
