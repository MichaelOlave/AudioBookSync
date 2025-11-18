"""
Database connection and utility module for AudioBookSync
Provides database connection management and common operations
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages PostgreSQL database connections using connection pooling"""

    _instance = None
    _pool = None

    def __new__(cls):
        """Singleton pattern to ensure only one connection pool"""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database connection pool"""
        if self._pool is None:
            self._initialize_pool()

    def _initialize_pool(self):
        """Create connection pool"""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'audiobooksync'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', ''),
                cursor_factory=RealDictCursor
            )
            logger.info("Database connection pool initialized successfully")
        except psycopg2.Error as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections

        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
        """
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, commit=True):
        """
        Context manager for database cursor

        Args:
            commit: Whether to auto-commit on success

        Usage:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM users")
                results = cursor.fetchall()
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def close_all_connections(self):
        """Close all connections in the pool"""
        if self._pool:
            self._pool.closeall()
            logger.info("All database connections closed")


class DatabaseOperations:
    """Common database operations for AudioBookSync"""

    def __init__(self):
        self.db = DatabaseConnection()

    # ============================================
    # USER OPERATIONS
    # ============================================

    def create_user(self, username: str, email: str, auth_file_path: str,
                   activation_bytes: str) -> Optional[str]:
        """
        Create a new user

        Returns:
            user_id if successful, None otherwise
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (username, email, auth_file_path, activation_bytes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING user_id
                """, (username, email, auth_file_path, activation_bytes))
                result = cursor.fetchone()
                user_id = str(result['user_id']) if result else None
                logger.info(f"Created user: {username} (ID: {user_id})")
                return user_id
        except psycopg2.IntegrityError as e:
            logger.error(f"User creation failed (duplicate): {e}")
            return None
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM users WHERE username = %s
                """, (username,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None

    def update_user_last_sync(self, user_id: str):
        """Update user's last sync timestamp"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE users
                    SET last_sync_date = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user_id,))
                logger.info(f"Updated last sync for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to update last sync: {e}")

    # ============================================
    # BOOK OPERATIONS
    # ============================================

    def add_book(self, asin: str, user_id: str, title: str,
                 purchase_date: str = None, runtime_min: int = None,
                 author: str = None, **kwargs) -> bool:
        """
        Add a new book to the library

        Args:
            asin: Amazon Standard Identification Number
            user_id: User UUID
            title: Book title
            purchase_date: Purchase date (YYYY-MM-DD)
            runtime_min: Runtime in minutes
            author: Author name
            **kwargs: Additional book metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
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
                """, (
                    asin, user_id, title, purchase_date, runtime_min,
                    author, kwargs.get('narrator'), kwargs.get('series_name'),
                    kwargs.get('description'), kwargs.get('rating')
                ))
                logger.info(f"Added/updated book: {title} (ASIN: {asin})")
                return True
        except Exception as e:
            logger.error(f"Failed to add book: {e}")
            return False

    def remove_book(self, asin: str) -> bool:
        """Remove a book from the library"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("DELETE FROM books WHERE asin = %s", (asin,))
                logger.info(f"Removed book: {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove book: {e}")
            return False

    def get_user_books(self, user_id: str) -> List[Dict]:
        """Get all books for a user"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM v_books_complete
                    WHERE user_id = %s
                    ORDER BY purchase_date DESC
                """, (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get user books: {e}")
            return []

    def get_book_by_asin(self, asin: str) -> Optional[Dict]:
        """Get book details by ASIN"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM v_books_complete WHERE asin = %s
                """, (asin,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get book: {e}")
            return None

    # ============================================
    # DOWNLOAD STATUS OPERATIONS
    # ============================================

    def create_download_status(self, asin: str, status: str = 'pending') -> Optional[str]:
        """Create a download status entry"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO download_status (asin, status, download_started_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    RETURNING download_id
                """, (asin, status))
                result = cursor.fetchone()
                download_id = str(result['download_id']) if result else None
                logger.info(f"Created download status for {asin}: {download_id}")
                return download_id
        except Exception as e:
            logger.error(f"Failed to create download status: {e}")
            return None

    def update_download_status(self, download_id: str, status: str,
                               download_path: str = None, file_size: int = None,
                               error_message: str = None) -> bool:
        """Update download status"""
        try:
            with self.db.get_cursor() as cursor:
                if status == 'completed':
                    cursor.execute("""
                        UPDATE download_status
                        SET status = %s,
                            download_path = %s,
                            file_size_bytes = %s,
                            download_completed_at = CURRENT_TIMESTAMP
                        WHERE download_id = %s
                    """, (status, download_path, file_size, download_id))
                elif status == 'failed':
                    cursor.execute("""
                        UPDATE download_status
                        SET status = %s,
                            error_message = %s
                        WHERE download_id = %s
                    """, (status, error_message, download_id))
                else:
                    cursor.execute("""
                        UPDATE download_status
                        SET status = %s
                        WHERE download_id = %s
                    """, (status, download_id))
                logger.info(f"Updated download status {download_id} to {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to update download status: {e}")
            return False

    # ============================================
    # DECRYPTION STATUS OPERATIONS
    # ============================================

    def create_decryption_status(self, asin: str, input_path: str,
                                 output_format: str = 'm4b') -> Optional[str]:
        """Create a decryption status entry"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO decryption_status (
                        asin, status, input_path, output_format,
                        decryption_started_at
                    )
                    VALUES (%s, 'pending', %s, %s, CURRENT_TIMESTAMP)
                    RETURNING decryption_id
                """, (asin, input_path, output_format))
                result = cursor.fetchone()
                decryption_id = str(result['decryption_id']) if result else None
                logger.info(f"Created decryption status for {asin}: {decryption_id}")
                return decryption_id
        except Exception as e:
            logger.error(f"Failed to create decryption status: {e}")
            return None

    def update_decryption_status(self, decryption_id: str, status: str,
                                 output_path: str = None, error_message: str = None) -> bool:
        """Update decryption status"""
        try:
            with self.db.get_cursor() as cursor:
                if status == 'completed':
                    cursor.execute("""
                        UPDATE decryption_status
                        SET status = %s,
                            output_path = %s,
                            decryption_completed_at = CURRENT_TIMESTAMP
                        WHERE decryption_id = %s
                    """, (status, output_path, decryption_id))
                elif status == 'failed':
                    cursor.execute("""
                        UPDATE decryption_status
                        SET status = %s,
                            error_message = %s
                        WHERE decryption_id = %s
                    """, (status, error_message, decryption_id))
                else:
                    cursor.execute("""
                        UPDATE decryption_status
                        SET status = %s
                        WHERE decryption_id = %s
                    """, (status, decryption_id))
                logger.info(f"Updated decryption status {decryption_id} to {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to update decryption status: {e}")
            return False

    # ============================================
    # SYNC HISTORY OPERATIONS
    # ============================================

    def create_sync_history(self, user_id: str, sync_type: str = 'full') -> Optional[str]:
        """Create a sync history entry"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sync_history (user_id, sync_type, status)
                    VALUES (%s, %s, 'in_progress')
                    RETURNING sync_id
                """, (user_id, sync_type))
                result = cursor.fetchone()
                sync_id = str(result['sync_id']) if result else None
                logger.info(f"Created sync history: {sync_id}")
                return sync_id
        except Exception as e:
            logger.error(f"Failed to create sync history: {e}")
            return None

    def complete_sync_history(self, sync_id: str, status: str,
                             books_found: int = 0, books_added: int = 0,
                             books_downloaded: int = 0, books_decrypted: int = 0,
                             errors_count: int = 0, notes: str = None) -> bool:
        """Complete a sync history entry"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    UPDATE sync_history
                    SET status = %s,
                        sync_completed_at = CURRENT_TIMESTAMP,
                        duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - sync_started_at)),
                        books_found = %s,
                        books_added = %s,
                        books_downloaded = %s,
                        books_decrypted = %s,
                        errors_count = %s,
                        notes = %s
                    WHERE sync_id = %s
                """, (status, books_found, books_added, books_downloaded,
                      books_decrypted, errors_count, notes, sync_id))
                logger.info(f"Completed sync history {sync_id} with status {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to complete sync history: {e}")
            return False

    # ============================================
    # ERROR LOGGING OPERATIONS
    # ============================================

    def log_error(self, error_type: str, error_message: str,
                  user_id: str = None, asin: str = None,
                  severity: str = 'error', **kwargs) -> bool:
        """Log an error to the database"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO error_log (
                        user_id, asin, error_type, error_message,
                        severity, stack_trace
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, asin, error_type, error_message,
                      severity, kwargs.get('stack_trace')))
                logger.info(f"Logged error: {error_type} - {error_message}")
                return True
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")
            return False


# Singleton instance
db_ops = DatabaseOperations()
