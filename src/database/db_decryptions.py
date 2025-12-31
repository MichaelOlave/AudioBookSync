"""Decryption status tracking database operations."""

from typing import Optional, List, Any

from loguru import logger

from .db_pool import DatabasePool  # noqa: F401
from .db_pool import db_pool as _db_pool


class DecryptionOperations:
    """Database operations for decryption status tracking."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_decryption_status(
        self,
        asin: str,
        download_id: Optional[str] = None,
        status: str = "pending",
        input_path: Optional[str] = None,
        output_format: str = "m4b",
    ) -> Optional[str]:
        """
        Create a decryption status entry.

        Args:
            asin: Amazon Standard Identification Number
            download_id: Associated download_id (foreign key)
            status: Initial status (default: 'pending')
            input_path: Path to encrypted file (optional)
            output_format: Target format (m4b, mp3, flac, aac)

        Returns:
            decryption_id if successful, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO decryption_status (
                        asin, download_id, status, input_path, output_format,
                        decryption_started_at
                    )
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING decryption_id
                """,
                    (asin, download_id, status, input_path, output_format),
                )
                result = cursor.fetchone()
                decryption_id = str(result["decryption_id"]) if result else None
                logger.info(f"Created decryption status for {asin}: {decryption_id}")
                return decryption_id
        except Exception as e:
            logger.error(f"Failed to create decryption status: {e}")
            return None

    def update_decryption_status(
        self,
        decryption_id: str,
        status: str,
        output_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update decryption status.

        Args:
            decryption_id: Decryption status UUID
            status: Status value (pending, decrypting, completed, failed, cancelled)
            output_path: Path to decrypted file
            error_message: Error details if failed

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                if status == "completed":
                    cursor.execute(
                        """
                        UPDATE decryption_status
                        SET status = %s,
                            output_path = %s,
                            decryption_completed_at = CURRENT_TIMESTAMP
                        WHERE decryption_id = %s
                    """,
                        (status, output_path, decryption_id),
                    )
                elif status == "failed":
                    cursor.execute(
                        """
                        UPDATE decryption_status
                        SET status = %s,
                            error_message = %s
                        WHERE decryption_id = %s
                    """,
                        (status, error_message, decryption_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE decryption_status
                        SET status = %s
                        WHERE decryption_id = %s
                    """,
                        (status, decryption_id),
                    )
                logger.info(f"Updated decryption status {decryption_id} to {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to update decryption status: {e}")
            return False

    def get_decryption_by_id(self, decryption_id: str) -> Optional[dict]:
        """
        Get a decryption record by decryption_id.

        Args:
            decryption_id: Decryption status UUID

        Returns:
            Decryption record if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ds.*, b.user_id, b.title
                    FROM decryption_status ds
                    LEFT JOIN books b ON ds.asin = b.asin
                    WHERE ds.decryption_id = %s
                """,
                    (decryption_id,),
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get decryption by ID {decryption_id}: {e}")
            return None

    def get_user_decryptions(
        self, user_id: str, status: Optional[str] = None, limit: int = 10, offset: int = 0
    ) -> List[dict]:
        """
        Get decryptions for a specific user with optional status filter.

        Joins with books table to ensure user ownership and to get additional metadata.

        Args:
            user_id: User UUID
            status: Optional status filter (pending, decrypting, completed, failed, cancelled)
            limit: Maximum number of records to return
            offset: Number of records to skip for pagination

        Returns:
            List of decryption records
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                query = """
                    SELECT ds.*, b.title, b.user_id
                    FROM decryption_status ds
                    JOIN books b ON ds.asin = b.asin
                    WHERE b.user_id = %s
                """
                params: List[Any] = [user_id]

                if status:
                    query += " AND ds.status = %s"
                    params.append(status)

                query += """
                    ORDER BY ds.decryption_started_at DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])

                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get user decryptions: {e}")
            return []

    def count_user_decryptions(self, user_id: str, status: Optional[str] = None) -> int:
        """
        Count decryptions for a user with optional status filter.

        Args:
            user_id: User UUID
            status: Optional status filter

        Returns:
            Total count of matching decryptions
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                query = """
                    SELECT COUNT(*) as count
                    FROM decryption_status ds
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
            logger.error(f"Failed to count user decryptions: {e}")
            return 0


# Singleton instance
decryption_ops = DecryptionOperations()
