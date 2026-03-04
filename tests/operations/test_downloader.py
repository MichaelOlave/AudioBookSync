"""Tests for src.operations.downloader module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.operations.downloader import download_book, validate_book


@pytest.mark.asyncio
@pytest.mark.unit
class TestDownloadBook:
    """Test book download functionality."""

    async def test_download_book_success(self, sample_book_data):
        """Test successful book download."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"
        audible_auth = {"locale_code": "us"}

        with patch(
            "src.operations.downloader.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            with patch("src.operations.downloader.os.listdir", return_value=[f"{book[0]}.aax"]):
                with patch("src.operations.downloader.os.path.exists", return_value=True):
                    with patch("src.operations.downloader.os.path.getsize", return_value=1024):
                        with patch(
                            "src.operations.downloader.decrypt_book_impl",
                            new_callable=AsyncMock,
                            return_value=True,
                        ) as mock_decrypt:
                            mock_process = AsyncMock()
                            mock_process.returncode = 0
                            mock_process.communicate = AsyncMock(return_value=(b"Downloaded", b""))
                            mock_exec.return_value = mock_process

                            result = await download_book(
                                book,
                                user_id=user_id,
                                audible_auth=audible_auth,
                                activation_bytes="test_bytes",
                            )

                            assert result is True
                            mock_decrypt.assert_called_once()

    async def test_download_book_calls_audible_cli(self, sample_book_data):
        """Test that download_book calls audible CLI."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"
        audible_auth = {"locale_code": "us"}

        with patch(
            "src.operations.downloader.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            with patch("src.operations.downloader.os.listdir", return_value=[f"{book[0]}.aax"]):
                with patch("src.operations.downloader.os.path.exists", return_value=True):
                    with patch("src.operations.downloader.os.path.getsize", return_value=1024):
                        with patch(
                            "src.operations.downloader.decrypt_book_impl",
                            new_callable=AsyncMock,
                            return_value=True,
                        ):
                            mock_process = AsyncMock()
                            mock_process.returncode = 0
                            mock_process.communicate = AsyncMock(return_value=(b"Downloaded", b""))
                            mock_exec.return_value = mock_process

                            await download_book(
                                book,
                                user_id=user_id,
                                audible_auth=audible_auth,
                                activation_bytes="test_bytes",
                            )

                            call_args = mock_exec.call_args[0]
                            assert "audible" in call_args
                            assert "download" in call_args
                            assert "--aax-fallback" in call_args
                            assert "asin_ascii" in call_args
                            assert sample_book_data["asin"] in call_args

    async def test_download_book_requires_user_id(self, sample_book_data):
        """Test download_book rejects missing user_id."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        result = await download_book(
            book,
            user_id="",
            audible_auth={"locale_code": "us"},
            activation_bytes="test_bytes",
        )

        assert result is False

    async def test_download_book_requires_audible_auth(self, sample_book_data):
        """Test download_book rejects missing Audible auth."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        result = await download_book(
            book,
            user_id="user-123",
            audible_auth=None,
            activation_bytes="test_bytes",
        )

        assert result is False

    async def test_download_book_process_failure(self, sample_book_data):
        """Test download_book handles process failure."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"
        audible_auth = {"locale_code": "us"}

        with patch(
            "src.operations.downloader.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.communicate = AsyncMock(return_value=(b"", b"Download failed"))
            mock_exec.return_value = mock_process

            result = await download_book(
                book,
                user_id=user_id,
                audible_auth=audible_auth,
                activation_bytes="test_bytes",
            )

            assert result is False

    async def test_download_book_no_new_files(self, sample_book_data):
        """Test download_book when no new files downloaded."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"
        audible_auth = {"locale_code": "us"}

        with patch(
            "src.operations.downloader.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(return_value=(b"No new files downloaded", b""))
            mock_exec.return_value = mock_process

            result = await download_book(
                book,
                user_id=user_id,
                audible_auth=audible_auth,
                activation_bytes="test_bytes",
            )

            assert result is False

    async def test_download_book_downloaded_file_missing(self, sample_book_data):
        """Test download_book when downloaded file is missing."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"
        audible_auth = {"locale_code": "us"}

        with patch(
            "src.operations.downloader.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            with patch("src.operations.downloader.os.listdir", return_value=[f"{book[0]}.aax"]):
                with patch("src.operations.downloader.os.path.exists", return_value=False):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(return_value=(b"Downloaded", b""))
                    mock_exec.return_value = mock_process

                    result = await download_book(
                        book,
                        user_id=user_id,
                        audible_auth=audible_auth,
                        activation_bytes="test_bytes",
                    )

                    assert result is False

    async def test_download_book_timeout_error(self, sample_book_data):
        """Test download_book handles timeout."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"
        audible_auth = {"locale_code": "us"}

        with patch(
            "src.operations.downloader.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.side_effect = asyncio.TimeoutError()

            result = await download_book(
                book,
                user_id=user_id,
                audible_auth=audible_auth,
                activation_bytes="test_bytes",
            )

            assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
class TestValidateBook:
    """Test book validation functionality."""

    async def test_validate_book_exists_by_asin(self, sample_book_data):
        """Test validate_book with file found by ASIN."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        mock_client = MagicMock()
        mock_client.file_exists.return_value = True
        mock_service = MagicMock()
        mock_service.minio_client = mock_client

        with patch("src.operations.downloader.StorageService", return_value=mock_service):
            result = await validate_book(book, user_id=user_id)

            assert result is True
            mock_client.file_exists.assert_called_once_with(
                "user-user-123",
                f"downloaded/{sample_book_data['asin']}.aax",
            )

    async def test_validate_book_not_exists(self, sample_book_data):
        """Test validate_book when file not found."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        mock_client = MagicMock()
        mock_client.file_exists.return_value = False
        mock_service = MagicMock()
        mock_service.minio_client = mock_client

        with patch("src.operations.downloader.StorageService", return_value=mock_service):
            result = await validate_book(book, user_id=user_id)

            assert result is False

    async def test_validate_book_requires_user(self, sample_book_data):
        """Test validate_book returns False without user_id."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        result = await validate_book(book, user_id="")

        assert result is False
