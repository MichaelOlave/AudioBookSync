"""PostgreSQL connection pooling and management."""

from contextlib import contextmanager
from urllib.parse import urlparse

import psycopg2
from loguru import logger
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from ..core.config import Config


class DatabasePool:
    """Singleton for managing PostgreSQL connection pooling."""

    _instance = None
    _pool = None

    def __new__(cls):
        """Ensure only one connection pool instance."""
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database pool (lazy initialization on first use)."""
        pass

    def _initialize_pool(self):
        """Create and configure the connection pool from DATABASE_URL."""
        if self._pool is not None:
            return  # Already initialized

        try:
            database_url = Config.DATABASE_URL
            parsed = urlparse(database_url)

            self._pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                database=parsed.path.lstrip("/") or "audiobooksync",
                user=parsed.username or "postgres",
                password=parsed.password or "",
                cursor_factory=RealDictCursor,
            )
            logger.info("Database connection pool initialized successfully")
        except psycopg2.Error as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Usage:
            with db_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
        """
        if self._pool is None:
            self._initialize_pool()
        assert self._pool is not None, "Pool should be initialized"
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
    def get_cursor(self, commit: bool = True):
        """
        Context manager for database cursor.

        Args:
            commit: Whether to auto-commit on success

        Usage:
            with db_pool.get_cursor() as cursor:
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
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("All database connections closed")


# Singleton instance
db_pool = DatabasePool()
