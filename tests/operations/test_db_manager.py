"""Tests for src.operations.db_manager module."""

from unittest.mock import AsyncMock, patch

import pytest

from src.operations.db_manager import LibraryManager, get_library_manager


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerInit:
    """Test LibraryManager initialization."""

    def test_init_stores_user_id(self):
        """Test that LibraryManager stores user_id."""
        manager = LibraryManager("user-123")
        assert manager.user_id == "user-123"

    def test_init_stores_book_ops(self):
        """Test that LibraryManager stores book_ops."""
        manager = LibraryManager("user-123")
        assert manager.book_ops is not None

    def test_init_stores_sync_ops(self):
        """Test that LibraryManager stores sync_ops."""
        manager = LibraryManager("user-123")
        assert manager.sync_ops is not None


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerAddBook:
    """Test add_book method."""

    async def test_add_book_success(self, sample_book_data):
        """Test successful book addition."""
        with patch("src.operations.db_manager.book_ops.add_book", return_value=True):
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                result = await manager.add_book(
                    asin=sample_book_data["asin"],
                    title=sample_book_data["title"],
                    author=sample_book_data["author"],
                )

                assert result is True

    async def test_add_book_calls_book_ops(self, sample_book_data):
        """Test that add_book calls book_ops.add_book."""
        with patch("src.operations.db_manager.book_ops.add_book", return_value=True) as mock_add:
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                await manager.add_book(
                    asin=sample_book_data["asin"], title=sample_book_data["title"]
                )

                mock_add.assert_called_once()

    async def test_add_book_failure(self, sample_book_data):
        """Test add_book handles failure."""
        with patch("src.operations.db_manager.book_ops.add_book", return_value=False):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.add_book(
                    asin=sample_book_data["asin"], title=sample_book_data["title"]
                )

                assert result is False

    async def test_add_book_exception(self, sample_book_data):
        """Test add_book handles exceptions."""
        with patch(
            "src.operations.db_manager.book_ops.add_book",
            side_effect=Exception("DB error"),
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.add_book(
                    asin=sample_book_data["asin"], title=sample_book_data["title"]
                )

                assert result is False

    async def test_add_book_with_all_fields(self, sample_book_data):
        """Test add_book with all optional fields."""
        with patch("src.operations.db_manager.book_ops.add_book", return_value=True) as mock_add:
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                await manager.add_book(
                    asin=sample_book_data["asin"],
                    title=sample_book_data["title"],
                    purchase_date=sample_book_data["purchase_date"],
                    runtime_min=sample_book_data["runtime_min"],
                    author=sample_book_data["author"],
                )

                call_kwargs = mock_add.call_args[1]
                assert call_kwargs["user_id"] == "user-123"


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerRemoveBook:
    """Test remove_book method."""

    async def test_remove_book_success(self):
        """Test successful book removal."""
        with patch("src.operations.db_manager.book_ops.remove_book", return_value=True):
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                result = await manager.remove_book("B001")

                assert result is True

    async def test_remove_book_failure(self):
        """Test remove_book failure."""
        with patch("src.operations.db_manager.book_ops.remove_book", return_value=False):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.remove_book("B001")

                assert result is False

    async def test_remove_book_exception(self):
        """Test remove_book exception handling."""
        with patch(
            "src.operations.db_manager.book_ops.remove_book",
            side_effect=Exception("DB error"),
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.remove_book("B001")

                assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerGetUserBooks:
    """Test get_user_books method."""

    async def test_get_user_books_success(self, sample_book_data):
        """Test successful book retrieval."""
        mock_books = [sample_book_data]

        with patch("src.operations.db_manager.book_ops.get_user_books", return_value=mock_books):
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                result = await manager.get_user_books()

                assert result == mock_books

    async def test_get_user_books_empty(self):
        """Test get_user_books with no books."""
        with patch("src.operations.db_manager.book_ops.get_user_books", return_value=[]):
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                result = await manager.get_user_books()

                assert result == []

    async def test_get_user_books_exception(self):
        """Test get_user_books exception handling."""
        with patch(
            "src.operations.db_manager.book_ops.get_user_books",
            side_effect=Exception("DB error"),
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.get_user_books()

                assert result == []


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerGetMissingBooks:
    """Test get_missing_books method."""

    async def test_get_missing_books_success(self, sample_book_data):
        """Test getting missing books."""
        book_with_status = {**sample_book_data, "is_downloaded": False}
        mock_books = [book_with_status]

        with patch(
            "src.operations.db_manager.LibraryManager.get_user_books",
            new_callable=AsyncMock,
            return_value=mock_books,
        ):
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                result = await manager.get_missing_books()

                assert len(result) == 1

    async def test_get_missing_books_filters_downloaded(self, sample_book_data):
        """Test that get_missing_books filters out downloaded books."""
        downloaded_book = {**sample_book_data, "is_downloaded": True}
        missing_book = {**sample_book_data, "is_downloaded": False}
        mock_books = [downloaded_book, missing_book]

        with patch(
            "src.operations.db_manager.LibraryManager.get_user_books",
            new_callable=AsyncMock,
            return_value=mock_books,
        ):
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                result = await manager.get_missing_books()

                assert len(result) == 1

    async def test_get_missing_books_exception(self):
        """Test get_missing_books exception handling."""
        with patch(
            "src.operations.db_manager.LibraryManager.get_user_books",
            new_callable=AsyncMock,
            side_effect=Exception("DB error"),
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.get_missing_books()

                assert result == []


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerBookExists:
    """Test book_exists method."""

    async def test_book_exists_true(self):
        """Test book_exists returns True when found."""
        mock_book = {"asin": "B001", "title": "Test"}

        with patch(
            "src.operations.db_manager.book_ops.get_book_by_asin",
            return_value=mock_book,
        ):
            manager = LibraryManager("user-123")
            result = await manager.book_exists("B001")

            assert result is True

    async def test_book_exists_false(self):
        """Test book_exists returns False when not found."""
        with patch("src.operations.db_manager.book_ops.get_book_by_asin", return_value=None):
            manager = LibraryManager("user-123")
            result = await manager.book_exists("B001")

            assert result is False

    async def test_book_exists_exception(self):
        """Test book_exists exception handling."""
        with patch(
            "src.operations.db_manager.book_ops.get_book_by_asin",
            side_effect=Exception("DB error"),
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.book_exists("B001")

                assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerCreateSync:
    """Test create_sync method."""

    async def test_create_sync_success(self):
        """Test successful sync creation."""
        with patch(
            "src.operations.db_manager.sync_ops.create_sync_history",
            return_value="sync-123",
        ):
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                result = await manager.create_sync("full")

                assert result == "sync-123"

    async def test_create_sync_default_type(self):
        """Test create_sync with default type."""
        with patch(
            "src.operations.db_manager.sync_ops.create_sync_history",
            return_value="sync-456",
        ) as mock_create:
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                await manager.create_sync()

                call_args = mock_create.call_args[0]
                assert call_args[1] == "full"

    async def test_create_sync_failure(self):
        """Test create_sync failure."""
        with patch("src.operations.db_manager.sync_ops.create_sync_history", return_value=None):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.create_sync("full")

                assert result is None

    async def test_create_sync_exception(self):
        """Test create_sync exception handling."""
        with patch(
            "src.operations.db_manager.sync_ops.create_sync_history",
            side_effect=Exception("DB error"),
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.create_sync("full")

                assert result is None


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerCompleteSync:
    """Test complete_sync method."""

    async def test_complete_sync_success(self):
        """Test successful sync completion."""
        with patch(
            "src.operations.db_manager.sync_ops.complete_sync_history",
            return_value=True,
        ):
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                result = await manager.complete_sync("sync-123", "completed")

                assert result is True

    async def test_complete_sync_with_stats(self):
        """Test complete_sync with statistics."""
        with patch(
            "src.operations.db_manager.sync_ops.complete_sync_history",
            return_value=True,
        ) as mock_complete:
            with patch("src.operations.db_manager.logger.info"):
                manager = LibraryManager("user-123")
                await manager.complete_sync(
                    "sync-123",
                    status="completed",
                    books_found=10,
                    books_downloaded=8,
                    books_decrypted=7,
                )

                call_kwargs = mock_complete.call_args[1]
                assert call_kwargs["books_found"] == 10

    async def test_complete_sync_failure(self):
        """Test complete_sync failure."""
        with patch(
            "src.operations.db_manager.sync_ops.complete_sync_history",
            return_value=False,
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.complete_sync("sync-123", "failed")

                assert result is False

    async def test_complete_sync_exception(self):
        """Test complete_sync exception handling."""
        with patch(
            "src.operations.db_manager.sync_ops.complete_sync_history",
            side_effect=Exception("DB error"),
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.complete_sync("sync-123", "failed")

                assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
class TestLibraryManagerLogError:
    """Test log_error method."""

    async def test_log_error_success(self):
        """Test successful error logging."""
        with patch("src.operations.db_manager.db_ops.errors.log_error", return_value=True):
            manager = LibraryManager("user-123")
            result = await manager.log_error(
                error_type="download_error", error_message="Test error"
            )

            assert result is True

    async def test_log_error_with_asin(self):
        """Test log_error with ASIN."""
        with patch(
            "src.operations.db_manager.db_ops.errors.log_error", return_value=True
        ) as mock_log:
            manager = LibraryManager("user-123")
            await manager.log_error(
                error_type="download_error", error_message="Test error", asin="B001"
            )

            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["asin"] == "B001"

    async def test_log_error_failure(self):
        """Test log_error failure."""
        with patch("src.operations.db_manager.db_ops.errors.log_error", return_value=False):
            manager = LibraryManager("user-123")
            result = await manager.log_error(
                error_type="download_error", error_message="Test error"
            )

            assert result is False

    async def test_log_error_exception(self):
        """Test log_error exception handling."""
        with patch(
            "src.operations.db_manager.db_ops.errors.log_error",
            side_effect=Exception("DB error"),
        ):
            with patch("src.operations.db_manager.logger.error"):
                manager = LibraryManager("user-123")
                result = await manager.log_error(
                    error_type="download_error", error_message="Test error"
                )

                assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetLibraryManager:
    """Test get_library_manager factory function."""

    async def test_get_library_manager_returns_instance(self):
        """Test get_library_manager returns LibraryManager instance."""
        result = await get_library_manager("user-123")

        assert isinstance(result, LibraryManager)

    async def test_get_library_manager_sets_user_id(self):
        """Test get_library_manager sets correct user_id."""
        result = await get_library_manager("user-456")

        assert result.user_id == "user-456"
