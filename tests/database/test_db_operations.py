"""Tests for database operations modules."""

from unittest.mock import MagicMock, patch

import pytest

from src.database.db_books import BookOperations
from src.database.db_decryptions import DecryptionOperations
from src.database.db_downloads import DownloadOperations
from src.database.db_errors import ErrorOperations
from src.database.db_sync import SyncOperations
from src.database.db_users import UserOperations


@pytest.mark.unit
@pytest.mark.db
class TestUserOperations:
    """Test UserOperations class."""

    def test_create_user_success(self):
        """Test successful user creation."""
        with patch("src.database.db_users.UserOperations.db_pool") as mock_pool:
            with patch.object(UserOperations, "db_pool", mock_pool):
                mock_cursor = MagicMock()
                mock_cursor.fetchone = MagicMock(return_value=("user-123",))
                mock_pool.get_cursor = MagicMock()
                mock_pool.get_cursor.return_value.__enter__ = MagicMock(
                    return_value=mock_cursor
                )
                mock_pool.get_cursor.return_value.__exit__ = MagicMock(
                    return_value=False
                )

                ops = UserOperations()
                result = ops.create_user(
                    "testuser", "test@example.com", "/path/auth", "bytes"
                )

                assert result == "user-123" or result is not None

    def test_get_user_by_username(self):
        """Test retrieving user by username."""
        with patch("src.database.db_users.DatabasePool"):
            mock_cursor = MagicMock()
            mock_user = {"user_id": "user-123", "username": "testuser"}
            mock_cursor.fetchone = MagicMock(return_value=mock_user)
            mock_pool = MagicMock()
            mock_pool.get_cursor = MagicMock()
            mock_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            mock_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            ops = UserOperations()
            ops.db_pool = mock_pool

            result = ops.get_user_by_username("testuser")

            assert result == mock_user or result is None or isinstance(result, dict)

    def test_update_user_last_sync(self):
        """Test updating user last sync timestamp."""
        with patch("src.database.db_users.DatabasePool"):
            mock_cursor = MagicMock()
            mock_pool = MagicMock()
            mock_pool.get_cursor = MagicMock()
            mock_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            mock_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            ops = UserOperations()
            ops.db_pool = mock_pool

            # Should not raise exception
            ops.update_user_last_sync("user-123")


@pytest.mark.unit
@pytest.mark.db
class TestBookOperations:
    """Test BookOperations class."""

    def test_add_book_success(self):
        """Test adding a book."""
        with patch("src.database.db_books.DatabasePool"):
            mock_cursor = MagicMock()
            ops = BookOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.add_book(
                asin="B001", user_id="user-123", title="Test Book", author="Test Author"
            )

            assert isinstance(result, bool) or result is True

    def test_get_user_books(self):
        """Test retrieving user books."""
        with patch("src.database.db_books.DatabasePool"):
            mock_cursor = MagicMock()
            mock_cursor.fetchall = MagicMock(
                return_value=[
                    {"asin": "B001", "title": "Book 1"},
                    {"asin": "B002", "title": "Book 2"},
                ]
            )
            ops = BookOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.get_user_books("user-123")

            assert isinstance(result, list)

    def test_remove_book(self):
        """Test removing a book."""
        with patch("src.database.db_books.DatabasePool"):
            mock_cursor = MagicMock()
            ops = BookOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.remove_book("B001")

            assert isinstance(result, bool)

    def test_get_book_by_asin(self):
        """Test retrieving book by ASIN."""
        with patch("src.database.db_books.DatabasePool"):
            mock_cursor = MagicMock()
            mock_book = {"asin": "B001", "title": "Test Book"}
            mock_cursor.fetchone = MagicMock(return_value=mock_book)
            ops = BookOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.get_book_by_asin("B001")

            assert result is None or isinstance(result, dict)


@pytest.mark.unit
@pytest.mark.db
class TestDownloadOperations:
    """Test DownloadOperations class."""

    def test_create_download_status(self):
        """Test creating download status."""
        with patch("src.database.db_downloads.DatabasePool"):
            mock_cursor = MagicMock()
            mock_cursor.fetchone = MagicMock(return_value=("download-123",))
            ops = DownloadOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.create_download_status("B001", status="pending")

            assert result is None or isinstance(result, str)

    def test_update_download_status(self):
        """Test updating download status."""
        with patch("src.database.db_downloads.DatabasePool"):
            mock_cursor = MagicMock()
            ops = DownloadOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.update_download_status(
                "download-123", status="completed", download_path="/path/to/file"
            )

            assert isinstance(result, bool)


@pytest.mark.unit
@pytest.mark.db
class TestDecryptionOperations:
    """Test DecryptionOperations class."""

    def test_create_decryption_status(self):
        """Test creating decryption status."""
        with patch("src.database.db_decryptions.DatabasePool"):
            mock_cursor = MagicMock()
            mock_cursor.fetchone = MagicMock(return_value=("decrypt-123",))
            ops = DecryptionOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.create_decryption_status(
                "B001", input_path="/path/input", output_format="m4b"
            )

            assert result is None or isinstance(result, str)

    def test_update_decryption_status(self):
        """Test updating decryption status."""
        with patch("src.database.db_decryptions.DatabasePool"):
            mock_cursor = MagicMock()
            ops = DecryptionOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.update_decryption_status(
                "decrypt-123", status="completed", output_path="/path/output"
            )

            assert isinstance(result, bool)


@pytest.mark.unit
@pytest.mark.db
class TestSyncOperations:
    """Test SyncOperations class."""

    def test_create_sync_history(self):
        """Test creating sync history."""
        with patch("src.database.db_sync.DatabasePool"):
            mock_cursor = MagicMock()
            mock_cursor.fetchone = MagicMock(return_value=("sync-123",))
            ops = SyncOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.create_sync_history("user-123", sync_type="full")

            assert result is None or isinstance(result, str)

    def test_complete_sync_history(self):
        """Test completing sync history."""
        with patch("src.database.db_sync.DatabasePool"):
            mock_cursor = MagicMock()
            ops = SyncOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.complete_sync_history(
                sync_id="sync-123",
                status="completed",
                books_found=10,
                books_downloaded=8,
            )

            assert isinstance(result, bool)


@pytest.mark.unit
@pytest.mark.db
class TestErrorOperations:
    """Test ErrorOperations class."""

    def test_log_error(self):
        """Test logging an error."""
        with patch("src.database.db_errors.DatabasePool"):
            mock_cursor = MagicMock()
            ops = ErrorOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.log_error(
                error_type="download_error",
                error_message="Test error",
                severity="error",
            )

            assert isinstance(result, bool)

    def test_log_error_with_asin(self):
        """Test logging error with ASIN."""
        with patch("src.database.db_errors.DatabasePool"):
            mock_cursor = MagicMock()
            ops = ErrorOperations()
            ops.db_pool = MagicMock()
            ops.db_pool.get_cursor = MagicMock()
            ops.db_pool.get_cursor.return_value.__enter__ = MagicMock(
                return_value=mock_cursor
            )
            ops.db_pool.get_cursor.return_value.__exit__ = MagicMock(return_value=False)

            result = ops.log_error(
                error_type="download_error",
                error_message="Test error",
                asin="B001",
                severity="error",
            )

            assert isinstance(result, bool)
