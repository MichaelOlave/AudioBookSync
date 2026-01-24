"""Tests for src.operations.library_sync module."""

from unittest.mock import AsyncMock, patch

import pytest

from src.operations.library_sync import get_or_create_user, process_book, sync_library


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetOrCreateUser:
    """Test user creation and retrieval."""

    async def test_get_existing_user(self):
        """Test retrieving an existing user."""
        mock_user = {
            "user_id": "user-123",
            "username": "michael",
            "email": "michael@example.com",
        }

        with patch(
            "src.operations.library_sync.user_ops.get_user_by_username",
            return_value=mock_user,
        ):
            with patch("src.operations.library_sync.logger.info"):
                user_id = await get_or_create_user("michael")

                assert user_id == "user-123"

    async def test_create_new_user(self):
        """Test creating a new user."""
        with patch(
            "src.operations.library_sync.user_ops.get_user_by_username",
            return_value=None,
        ):
            with patch(
                "src.operations.library_sync.user_ops.create_user",
                return_value="user-456",
            ) as mock_create:
                with patch("src.operations.library_sync.logger.info"):
                    user_id = await get_or_create_user("newuser")

                    assert user_id == "user-456"
                    mock_create.assert_called_once()

    async def test_create_user_with_config_values(self):
        """Test that create_user is called with config values."""
        with patch(
            "src.operations.library_sync.user_ops.get_user_by_username",
            return_value=None,
        ):
            with patch(
                "src.operations.library_sync.user_ops.create_user",
                return_value="user-456",
            ) as mock_create:
                with patch("src.operations.library_sync.Config.AUTH_FILE", "/path/to/auth.json"):
                    with patch(
                        "src.operations.library_sync.Config.ACTIVATION_BYTES",
                        "test_bytes",
                    ):
                        with patch("src.operations.library_sync.logger.info"):
                            await get_or_create_user("testuser")

                            call_kwargs = mock_create.call_args[1]
                            assert call_kwargs["auth_file_path"] == "/path/to/auth.json"
                            assert call_kwargs["activation_bytes"] == "test_bytes"

    async def test_create_user_failure(self):
        """Test user creation failure raises error."""
        with patch(
            "src.operations.library_sync.user_ops.get_user_by_username",
            return_value=None,
        ):
            with patch("src.operations.library_sync.user_ops.create_user", return_value=None):
                with pytest.raises(RuntimeError):
                    await get_or_create_user("failuser")

    async def test_default_username(self):
        """Test default username parameter."""
        mock_user = {"user_id": "user-123"}

        with patch(
            "src.operations.library_sync.user_ops.get_user_by_username",
            return_value=mock_user,
        ) as mock_get:
            with patch("src.operations.library_sync.logger.info"):
                await get_or_create_user()

                mock_get.assert_called_once_with("michael")

    async def test_custom_username(self):
        """Test custom username parameter."""
        mock_user = {"user_id": "user-789"}

        with patch(
            "src.operations.library_sync.user_ops.get_user_by_username",
            return_value=mock_user,
        ) as mock_get:
            with patch("src.operations.library_sync.logger.info"):
                await get_or_create_user("customuser")

                mock_get.assert_called_once_with("customuser")

    async def test_logs_existing_user(self):
        """Test that existing user retrieval is logged."""
        mock_user = {"user_id": "user-123"}

        with patch(
            "src.operations.library_sync.user_ops.get_user_by_username",
            return_value=mock_user,
        ):
            with patch("src.operations.library_sync.logger.info") as mock_logger:
                await get_or_create_user("michael")

                mock_logger.assert_called()

    async def test_logs_new_user(self):
        """Test that new user creation is logged."""
        with patch(
            "src.operations.library_sync.user_ops.get_user_by_username",
            return_value=None,
        ):
            with patch(
                "src.operations.library_sync.user_ops.create_user",
                return_value="user-456",
            ):
                with patch("src.operations.library_sync.logger.info") as mock_logger:
                    await get_or_create_user("newuser")

                    assert mock_logger.call_count >= 1


@pytest.mark.asyncio
@pytest.mark.unit
class TestSyncLibrary:
    """Test library synchronization workflow."""

    async def test_sync_library_success(self):
        """Test successful sync workflow."""
        mock_library_manager = AsyncMock()
        mock_library_manager.create_sync = AsyncMock(return_value="sync-123")
        mock_library_manager.get_missing_books = AsyncMock(return_value=[])
        mock_library_manager.complete_sync = AsyncMock(return_value=True)

        with patch("src.operations.library_sync.Config.ensure_directories"):
            with patch(
                "src.operations.library_sync.get_or_create_user",
                new_callable=AsyncMock,
                return_value="user-123",
            ):
                with patch(
                    "src.operations.library_sync.get_library_manager",
                    new_callable=AsyncMock,
                    return_value=mock_library_manager,
                ):
                    with patch("src.operations.library_sync.logger.info"):
                        await sync_library()

                        mock_library_manager.complete_sync.assert_called_once()

    async def test_sync_library_ensures_directories(self):
        """Test that sync_library ensures directories."""
        mock_library_manager = AsyncMock()
        mock_library_manager.create_sync = AsyncMock(return_value="sync-123")
        mock_library_manager.get_missing_books = AsyncMock(return_value=[])
        mock_library_manager.complete_sync = AsyncMock(return_value=True)

        with patch("src.operations.library_sync.Config.ensure_directories") as mock_ensure:
            with patch(
                "src.operations.library_sync.get_or_create_user",
                new_callable=AsyncMock,
                return_value="user-123",
            ):
                with patch(
                    "src.operations.library_sync.get_library_manager",
                    new_callable=AsyncMock,
                    return_value=mock_library_manager,
                ):
                    with patch("src.operations.library_sync.logger.info"):
                        await sync_library()

                        mock_ensure.assert_called_once()

    async def test_sync_library_creates_sync_record(self):
        """Test that sync_library creates sync record."""
        mock_library_manager = AsyncMock()
        mock_library_manager.create_sync = AsyncMock(return_value="sync-123")
        mock_library_manager.get_missing_books = AsyncMock(return_value=[])
        mock_library_manager.complete_sync = AsyncMock(return_value=True)

        with patch("src.operations.library_sync.Config.ensure_directories"):
            with patch(
                "src.operations.library_sync.get_or_create_user",
                new_callable=AsyncMock,
                return_value="user-123",
            ):
                with patch(
                    "src.operations.library_sync.get_library_manager",
                    new_callable=AsyncMock,
                    return_value=mock_library_manager,
                ):
                    with patch("src.operations.library_sync.logger.info"):
                        await sync_library()

                        mock_library_manager.create_sync.assert_called_once_with("full")

    async def test_sync_library_handles_missing_books(self):
        """Test sync_library processes missing books."""
        mock_books = [
            {
                "asin": "B001",
                "title": "Book 1",
                "is_downloaded": False,
                "is_decrypted": False,
            }
        ]
        mock_library_manager = AsyncMock()
        mock_library_manager.create_sync = AsyncMock(return_value="sync-123")
        mock_library_manager.get_missing_books = AsyncMock(return_value=mock_books)
        mock_library_manager.complete_sync = AsyncMock(return_value=True)

        with patch("src.operations.library_sync.Config.ensure_directories"):
            with patch(
                "src.operations.library_sync.get_or_create_user",
                new_callable=AsyncMock,
                return_value="user-123",
            ):
                with patch(
                    "src.operations.library_sync.get_library_manager",
                    new_callable=AsyncMock,
                    return_value=mock_library_manager,
                ):
                    with patch(
                        "src.operations.library_sync.process_book",
                        new_callable=AsyncMock,
                    ):
                        with patch("src.operations.library_sync.logger.info"):
                            await sync_library()

                            mock_library_manager.get_missing_books.assert_called_once()

    async def test_sync_library_completes_sync_record(self):
        """Test sync_library completes sync record."""
        mock_library_manager = AsyncMock()
        mock_library_manager.create_sync = AsyncMock(return_value="sync-123")
        mock_library_manager.get_missing_books = AsyncMock(return_value=[])
        mock_library_manager.complete_sync = AsyncMock(return_value=True)

        with patch("src.operations.library_sync.Config.ensure_directories"):
            with patch(
                "src.operations.library_sync.get_or_create_user",
                new_callable=AsyncMock,
                return_value="user-123",
            ):
                with patch(
                    "src.operations.library_sync.get_library_manager",
                    new_callable=AsyncMock,
                    return_value=mock_library_manager,
                ):
                    with patch("src.operations.library_sync.logger.info"):
                        await sync_library()

                        call_kwargs = mock_library_manager.complete_sync.call_args[1]
                        assert call_kwargs["sync_id"] == "sync-123"
                        assert call_kwargs["status"] == "completed"

    async def test_sync_library_handles_sync_creation_failure(self):
        """Test sync_library handles sync creation failure."""
        mock_library_manager = AsyncMock()
        mock_library_manager.create_sync = AsyncMock(return_value=None)

        with patch("src.operations.library_sync.Config.ensure_directories"):
            with patch(
                "src.operations.library_sync.get_or_create_user",
                new_callable=AsyncMock,
                return_value="user-123",
            ):
                with patch(
                    "src.operations.library_sync.get_library_manager",
                    new_callable=AsyncMock,
                    return_value=mock_library_manager,
                ):
                    with patch("src.operations.library_sync.logger.error"):
                        await sync_library()

                        mock_library_manager.complete_sync.assert_not_called()

    async def test_sync_library_handles_exception(self):
        """Test sync_library handles exceptions."""
        with patch("src.operations.library_sync.Config.ensure_directories") as mock_ensure:
            mock_ensure.side_effect = Exception("Config error")
            with patch("src.operations.library_sync.logger.error"):
                await sync_library()

    async def test_sync_library_concurrent_processing(self):
        """Test sync_library processes books concurrently."""
        mock_books = [
            {
                "asin": "B001",
                "title": "Book 1",
                "is_downloaded": False,
                "is_decrypted": False,
            },
            {
                "asin": "B002",
                "title": "Book 2",
                "is_downloaded": False,
                "is_decrypted": False,
            },
        ]
        mock_library_manager = AsyncMock()
        mock_library_manager.create_sync = AsyncMock(return_value="sync-123")
        mock_library_manager.get_missing_books = AsyncMock(return_value=mock_books)
        mock_library_manager.complete_sync = AsyncMock(return_value=True)

        with patch("src.operations.library_sync.Config.ensure_directories"):
            with patch(
                "src.operations.library_sync.get_or_create_user",
                new_callable=AsyncMock,
                return_value="user-123",
            ):
                with patch(
                    "src.operations.library_sync.get_library_manager",
                    new_callable=AsyncMock,
                    return_value=mock_library_manager,
                ):
                    with patch(
                        "src.operations.library_sync.process_book",
                        new_callable=AsyncMock,
                    ) as mock_process:
                        with patch("src.operations.library_sync.logger.info"):
                            await sync_library()

                            assert mock_process.call_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
class TestProcessBook:
    """Test individual book processing."""

    async def test_process_book_success(self):
        """Test successful book processing."""
        mock_book = {"asin": "B001", "title": "Test Book"}
        mock_library_manager = AsyncMock()

        with patch(
            "src.operations.library_sync.download_book",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch(
                "src.operations.library_sync.decrypt_book",
                new_callable=AsyncMock,
                return_value=True,
            ):
                with patch("src.operations.library_sync.logger.info"):
                    await process_book("user-123", mock_book, mock_library_manager)

                    mock_library_manager.log_error.assert_not_called()

    async def test_process_book_downloads_book(self):
        """Test process_book downloads book."""
        mock_book = {"asin": "B001", "title": "Test Book"}
        mock_library_manager = AsyncMock()

        with patch(
            "src.operations.library_sync.download_book",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_download:
            with patch(
                "src.operations.library_sync.decrypt_book",
                new_callable=AsyncMock,
                return_value=True,
            ):
                with patch("src.operations.library_sync.logger.info"):
                    await process_book("user-123", mock_book, mock_library_manager)

                    mock_download.assert_called_once_with(["B001", "Test Book"])

    async def test_process_book_decrypts_book(self):
        """Test process_book decrypts book."""
        mock_book = {"asin": "B001", "title": "Test Book"}
        mock_library_manager = AsyncMock()

        with patch(
            "src.operations.library_sync.download_book",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch(
                "src.operations.library_sync.decrypt_book",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_decrypt:
                with patch("src.operations.library_sync.logger.info"):
                    await process_book("user-123", mock_book, mock_library_manager)

                    mock_decrypt.assert_called_once_with(["B001", "Test Book"])

    async def test_process_book_download_failure(self):
        """Test process_book handles download failure."""
        mock_book = {"asin": "B001", "title": "Test Book"}
        mock_library_manager = AsyncMock()

        with patch(
            "src.operations.library_sync.download_book",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch("src.operations.library_sync.logger.error"):
                await process_book("user-123", mock_book, mock_library_manager)

                mock_library_manager.log_error.assert_called_once()

    async def test_process_book_decryption_failure(self):
        """Test process_book handles decryption failure."""
        mock_book = {"asin": "B001", "title": "Test Book"}
        mock_library_manager = AsyncMock()

        with patch(
            "src.operations.library_sync.download_book",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch(
                "src.operations.library_sync.decrypt_book",
                new_callable=AsyncMock,
                return_value=False,
            ):
                with patch("src.operations.library_sync.logger.error"):
                    await process_book("user-123", mock_book, mock_library_manager)

                    mock_library_manager.log_error.assert_called_once()

    async def test_process_book_logs_error(self):
        """Test process_book logs errors."""
        mock_book = {"asin": "B001", "title": "Test Book"}
        mock_library_manager = AsyncMock()

        with patch(
            "src.operations.library_sync.download_book",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch("src.operations.library_sync.logger.error") as mock_logger:
                await process_book("user-123", mock_book, mock_library_manager)

                mock_logger.assert_called()

    async def test_process_book_logs_error_with_asin(self):
        """Test process_book logs error with ASIN."""
        mock_book = {"asin": "B001", "title": "Test Book"}
        mock_library_manager = AsyncMock()

        with patch(
            "src.operations.library_sync.download_book",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with patch("src.operations.library_sync.logger.error"):
                await process_book("user-123", mock_book, mock_library_manager)

                call_kwargs = mock_library_manager.log_error.call_args[1]
                assert call_kwargs["asin"] == "B001"

    async def test_process_book_exception_handling(self):
        """Test process_book handles exceptions."""
        mock_book = {"asin": "B001", "title": "Test Book"}
        mock_library_manager = AsyncMock()

        with patch(
            "src.operations.library_sync.download_book",
            new_callable=AsyncMock,
            side_effect=Exception("Network error"),
        ):
            with patch("src.operations.library_sync.logger.error"):
                await process_book("user-123", mock_book, mock_library_manager)

                mock_library_manager.log_error.assert_called_once()
