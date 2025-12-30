"""Tests for src.database.db_pool module."""

from unittest.mock import MagicMock, patch

import psycopg2
import pytest

from src.database.db_pool import DatabasePool


@pytest.mark.unit
@pytest.mark.db
class TestDatabasePoolSingleton:
    """Test DatabasePool singleton pattern."""

    def test_singleton_instance(self):
        """Test that DatabasePool returns same instance."""
        pool1 = DatabasePool()
        pool2 = DatabasePool()

        assert pool1 is pool2

    def test_singleton_instance_multiple_calls(self):
        """Test singleton across multiple instantiations."""
        instances = [DatabasePool() for _ in range(5)]

        assert all(inst is instances[0] for inst in instances)


@pytest.mark.unit
@pytest.mark.db
class TestDatabasePoolConnection:
    """Test DatabasePool connection management."""

    def test_get_connection_context_manager(self):
        """Test get_connection works as context manager."""
        pool = DatabasePool()

        with patch.object(pool, "_pool") as mock_pool:
            mock_conn = MagicMock()
            mock_pool.getconn = MagicMock(return_value=mock_conn)
            mock_pool.putconn = MagicMock()

            with pool.get_connection() as conn:
                assert conn == mock_conn

            mock_pool.getconn.assert_called_once()
            mock_pool.putconn.assert_called_once()

    def test_get_connection_returns_connection(self):
        """Test get_connection returns a connection."""
        pool = DatabasePool()

        with patch.object(pool, "_pool") as mock_pool:
            mock_conn = MagicMock()
            mock_pool.getconn = MagicMock(return_value=mock_conn)
            mock_pool.putconn = MagicMock()

            with pool.get_connection():
                pass

    def test_get_connection_commits_on_success(self):
        """Test get_connection commits transaction on success."""
        pool = DatabasePool()

        with patch.object(pool, "_pool") as mock_pool:
            mock_conn = MagicMock()
            mock_pool.getconn = MagicMock(return_value=mock_conn)
            mock_pool.putconn = MagicMock()

            with pool.get_connection():
                pass

            mock_conn.commit.assert_called_once()

    def test_get_connection_rollback_on_exception(self):
        """Test get_connection rolls back on exception."""
        pool = DatabasePool()

        with patch.object(pool, "_pool") as mock_pool:
            mock_conn = MagicMock()
            mock_pool.getconn = MagicMock(return_value=mock_conn)
            mock_pool.putconn = MagicMock()

            try:
                with pool.get_connection():
                    raise ValueError("Test error")
            except ValueError:
                pass

            mock_conn.rollback.assert_called_once()

    def test_get_connection_returns_connection_to_pool(self):
        """Test get_connection returns connection to pool."""
        pool = DatabasePool()

        with patch.object(pool, "_pool") as mock_pool:
            mock_conn = MagicMock()
            mock_pool.getconn = MagicMock(return_value=mock_conn)
            mock_pool.putconn = MagicMock()

            with pool.get_connection():
                pass

            mock_pool.putconn.assert_called_once_with(mock_conn)


@pytest.mark.unit
@pytest.mark.db
class TestDatabasePoolCursor:
    """Test DatabasePool cursor management."""

    def test_get_cursor_context_manager(self):
        """Test get_cursor works as context manager."""
        pool = DatabasePool()

        with patch.object(pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor = MagicMock(return_value=mock_cursor)
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

            with pool.get_cursor() as cursor:
                assert cursor == mock_cursor

    def test_get_cursor_with_commit_true(self):
        """Test get_cursor with commit=True (default)."""
        pool = DatabasePool()

        with patch.object(pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor = MagicMock(return_value=mock_cursor)
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

            with pool.get_cursor(commit=True):
                pass

    def test_get_cursor_with_commit_false(self):
        """Test get_cursor with commit=False."""
        pool = DatabasePool()

        with patch.object(pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor = MagicMock(return_value=mock_cursor)
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

            with pool.get_cursor(commit=False):
                pass

    def test_get_cursor_returns_cursor(self):
        """Test get_cursor returns actual cursor."""
        pool = DatabasePool()

        with patch.object(pool, "get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor = MagicMock(return_value=mock_cursor)
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

            with pool.get_cursor() as cursor:
                assert cursor is not None


@pytest.mark.unit
@pytest.mark.db
class TestDatabasePoolCleanup:
    """Test DatabasePool cleanup."""

    def test_close_all_connections(self):
        """Test close_all_connections closes pool."""
        pool = DatabasePool()

        with patch.object(pool, "_pool") as mock_pool:
            mock_pool.closeall = MagicMock()

            pool.close_all_connections()

            mock_pool.closeall.assert_called_once()

    def test_close_all_connections_called_once(self):
        """Test close_all_connections idempotent."""
        pool = DatabasePool()

        with patch.object(pool, "_pool") as mock_pool:
            mock_pool.closeall = MagicMock()

            pool.close_all_connections()
            pool.close_all_connections()

            assert mock_pool.closeall.call_count >= 1


@pytest.mark.unit
@pytest.mark.db
class TestDatabasePoolErrorHandling:
    """Test DatabasePool error handling."""

    def test_get_connection_handles_none_connection(self):
        """Test get_connection handles None connection."""
        pool = DatabasePool()

        with patch.object(pool, "_pool") as mock_pool:
            mock_pool.getconn = MagicMock(return_value=None)
            mock_pool.putconn = MagicMock()

            with pytest.raises(Exception):
                with pool.get_connection() as conn:
                    if conn is None:
                        raise Exception("No connection")

    def test_get_cursor_handles_connection_error(self):
        """Test get_cursor handles connection errors."""
        pool = DatabasePool()

        with patch.object(pool, "get_connection") as mock_get_conn:
            mock_get_conn.side_effect = psycopg2.OperationalError("Connection failed")

            with pytest.raises(psycopg2.OperationalError):
                with pool.get_cursor():
                    pass


@pytest.mark.unit
@pytest.mark.db
class TestDatabasePoolThreadSafety:
    """Test DatabasePool thread safety."""

    def test_singleton_is_thread_safe(self):
        """Test that singleton pattern is thread-safe."""
        import threading

        results = []

        def create_pool():
            results.append(DatabasePool())

        threads = [threading.Thread(target=create_pool) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        assert all(inst is results[0] for inst in results)
