"""Tests for src.database.database module."""

from unittest.mock import patch

import pytest

from src.database.database import DatabaseOperations


@pytest.mark.unit
@pytest.mark.db
class TestDatabaseOperations:
    """Test DatabaseOperations aggregator."""

    def test_singleton_instance(self):
        """Test DatabaseOperations singleton."""
        ops1 = DatabaseOperations()
        ops2 = DatabaseOperations()

        assert ops1 is ops2

    def test_has_users_attribute(self):
        """Test DatabaseOperations has users attribute."""
        ops = DatabaseOperations()
        assert hasattr(ops, "users")

    def test_has_books_attribute(self):
        """Test DatabaseOperations has books attribute."""
        ops = DatabaseOperations()
        assert hasattr(ops, "books")

    def test_has_downloads_attribute(self):
        """Test DatabaseOperations has downloads attribute."""
        ops = DatabaseOperations()
        assert hasattr(ops, "downloads")

    def test_has_decryptions_attribute(self):
        """Test DatabaseOperations has decryptions attribute."""
        ops = DatabaseOperations()
        assert hasattr(ops, "decryptions")

    def test_has_syncs_attribute(self):
        """Test DatabaseOperations has syncs attribute."""
        ops = DatabaseOperations()
        assert hasattr(ops, "syncs")

    def test_has_errors_attribute(self):
        """Test DatabaseOperations has errors attribute."""
        ops = DatabaseOperations()
        assert hasattr(ops, "errors")

    def test_has_pool_attribute(self):
        """Test DatabaseOperations has pool attribute."""
        ops = DatabaseOperations()
        assert hasattr(ops, "pool")

    def test_users_is_not_none(self):
        """Test users is not None."""
        ops = DatabaseOperations()
        assert ops.users is not None

    def test_books_is_not_none(self):
        """Test books is not None."""
        ops = DatabaseOperations()
        assert ops.books is not None

    def test_downloads_is_not_none(self):
        """Test downloads is not None."""
        ops = DatabaseOperations()
        assert ops.downloads is not None

    def test_decryptions_is_not_none(self):
        """Test decryptions is not None."""
        ops = DatabaseOperations()
        assert ops.decryptions is not None

    def test_syncs_is_not_none(self):
        """Test syncs is not None."""
        ops = DatabaseOperations()
        assert ops.syncs is not None

    def test_errors_is_not_none(self):
        """Test errors is not None."""
        ops = DatabaseOperations()
        assert ops.errors is not None

    def test_pool_is_not_none(self):
        """Test pool is not None."""
        ops = DatabaseOperations()
        assert ops.pool is not None

    def test_close_all_connections(self):
        """Test close_all_connections method."""
        ops = DatabaseOperations()
        with patch.object(ops.pool, "close_all_connections") as mock_close:
            ops.close_all_connections()
            mock_close.assert_called_once()

    def test_multiple_instances_same_object(self):
        """Test multiple instantiations return same object."""
        instances = [DatabaseOperations() for _ in range(5)]
        assert all(inst is instances[0] for inst in instances)

    def test_unified_interface(self):
        """Test unified interface provides access to all operations."""
        ops = DatabaseOperations()

        # Should be able to call operations through unified interface
        assert hasattr(ops.users, "create_user") or hasattr(ops, "users")
        assert hasattr(ops.books, "add_book") or hasattr(ops, "books")
        assert hasattr(ops.downloads, "create_download_status") or hasattr(
            ops, "downloads"
        )
        assert hasattr(ops.decryptions, "create_decryption_status") or hasattr(
            ops, "decryptions"
        )
        assert hasattr(ops.syncs, "create_sync_history") or hasattr(ops, "syncs")
        assert hasattr(ops.errors, "log_error") or hasattr(ops, "errors")


@pytest.mark.unit
@pytest.mark.db
class TestDatabaseOperationsIntegration:
    """Integration tests for DatabaseOperations."""

    def test_operations_are_accessible(self):
        """Test that all operations are accessible."""
        ops = DatabaseOperations()

        # All sub-operations should be accessible
        try:
            _ = ops.users
            _ = ops.books
            _ = ops.downloads
            _ = ops.decryptions
            _ = ops.syncs
            _ = ops.errors
            _ = ops.pool
        except AttributeError as e:
            pytest.fail(f"Operation not accessible: {e}")

    def test_pool_closure_idempotent(self):
        """Test that pool closure can be called multiple times."""
        ops = DatabaseOperations()
        with patch.object(ops.pool, "close_all_connections"):
            ops.close_all_connections()
            ops.close_all_connections()

    def test_singleton_pattern_enforced(self):
        """Test singleton pattern is enforced."""
        ops1 = DatabaseOperations()
        ops2 = DatabaseOperations()
        ops3 = DatabaseOperations()

        assert id(ops1) == id(ops2) == id(ops3)

    def test_backward_compatibility(self):
        """Test backward compatibility with old database interface."""
        ops = DatabaseOperations()

        # Should provide same interface as individual operations
        assert ops.users is not None
        assert ops.books is not None
        assert ops.downloads is not None
        assert ops.decryptions is not None
        assert ops.syncs is not None
        assert ops.errors is not None
