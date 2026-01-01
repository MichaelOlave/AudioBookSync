"""Download status tracking database operations."""

from typing import Optional, List, Any

from loguru import logger

from .db_pool import DatabasePool  # noqa: F401
from .db_pool import db_pool as _db_pool


class DownloadOperations:
    """Database operations for download status tracking."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_download_status(
        self, asin: str, status: str = "pending"
    ) -> Optional[str]:
        """
        Create a download status entry.

        Args:
            asin: Amazon Standard Identification Number
            status: Initial status (default: 'pending')

        Returns:
            download_id if successful, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO download_status (asin, status, download_started_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    RETURNING download_id
                """,
                    (asin, status),
                )
                result = cursor.fetchone()
                download_id = str(result["download_id"]) if result else None
                logger.info(f"Created download status for {asin}: {download_id}")
                return download_id
        except Exception as e:
            logger.error(f"Failed to create download status: {e}")
            return None

    def update_download_status(
        self,
        download_id: str,
        status: str,
        download_path: Optional[str] = None,
        file_size: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update download status.

        Args:
            download_id: Download status UUID
            status: Status value (pending, downloading, completed, failed, cancelled)
            download_path: Path to downloaded file
            file_size: File size in bytes
            error_message: Error details if failed

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                if status == "completed":
                    cursor.execute(
                        """
                        UPDATE download_status
                        SET status = %s,
                            download_path = %s,
                            file_size_bytes = %s,
                            download_completed_at = CURRENT_TIMESTAMP
                        WHERE download_id = %s
                    """,
                        (status, download_path, file_size, download_id),
                    )
                elif status == "failed":
                    cursor.execute(
                        """
                        UPDATE download_status
                        SET status = %s,
                            error_message = %s
                        WHERE download_id = %s
                    """,
                        (status, error_message, download_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE download_status
                        SET status = %s
                        WHERE download_id = %s
                    """,
                        (status, download_id),
                    )
                logger.info(f"Updated download status {download_id} to {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to update download status: {e}")
            return False

    def update_download_object_key(
        self, download_id: str, object_key: str
    ) -> bool:
        """
        Update download status with MinIO object_key.

        Args:
            download_id: Download status UUID
            object_key: MinIO object key for the downloaded file

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE download_status
                    SET object_key = %s
                    WHERE download_id = %s
                """,
                    (object_key, download_id),
                )
                logger.info(f"Updated download {download_id} with object_key: {object_key}")
                return True
        except Exception as e:
            logger.error(f"Failed to update download object_key: {e}")
            return False

    def get_download_by_id(self, download_id: str) -> Optional[dict]:
        """
        Get a download record by download_id.

        Args:
            download_id: Download status UUID

        Returns:
            Download record if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ds.*, b.user_id, b.title
                    FROM download_status ds
                    LEFT JOIN books b ON ds.asin = b.asin
                    WHERE ds.download_id = %s
                """,
                    (download_id,),
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get download by ID {download_id}: {e}")
            return None

    def get_download_by_asin(self, asin: str) -> Optional[dict]:
        """
        Get a download record by ASIN.

        Used to check if a book has been downloaded before allowing decryption.

        Args:
            asin: Amazon Standard Identification Number

        Returns:
            Download record if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ds.*
                    FROM download_status ds
                    WHERE ds.asin = %s
                    ORDER BY ds.download_started_at DESC
                    LIMIT 1
                """,
                    (asin,),
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get download by ASIN {asin}: {e}")
            return None

    def get_user_downloads(
        self, user_id: str, status: Optional[str] = None, limit: int = 10, offset: int = 0
    ) -> List[dict]:
        """
        Get downloads for a specific user with optional status filter.

        Joins with books table to ensure user ownership and to get additional metadata.

        Args:
            user_id: User UUID
            status: Optional status filter (pending, downloading, completed, failed, cancelled)
            limit: Maximum number of records to return
            offset: Number of records to skip for pagination

        Returns:
            List of download records
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                query = """
                    SELECT ds.*, b.title, b.user_id
                    FROM download_status ds
                    JOIN books b ON ds.asin = b.asin
                    WHERE b.user_id = %s
                """
                params: List[Any] = [user_id]

                if status:
                    query += " AND ds.status = %s"
                    params.append(status)

                query += """
                    ORDER BY ds.download_started_at DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])

                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get user downloads: {e}")
            return []

    def count_user_downloads(self, user_id: str, status: Optional[str] = None) -> int:
        """
        Count downloads for a user with optional status filter.

        Args:
            user_id: User UUID
            status: Optional status filter

        Returns:
            Total count of matching downloads
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                query = """
                    SELECT COUNT(*) as count
                    FROM download_status ds
                    JOIN books b ON ds.asin = b.asin
                    WHERE b.user_id = %s
                """
                params = [user_id]

                if status:
                    query += " AND ds.status = %s"
                    params.append(status)

                cursor.execute(query, params)
                result = cursor.fetchone()
                return result["count"] if result else 0
        except Exception as e:
            logger.error(f"Failed to count user downloads: {e}")
            return 0


# Singleton instance
download_ops = DownloadOperations()
