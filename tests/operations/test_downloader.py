"""Tests for src.operations.downloader module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.operations.downloader import download_book, validate_book


@pytest.mark.asyncio
@pytest.mark.unit
class TestDownloadBook:
    """Test book download functionality."""

    async def test_download_book_success(self, sample_book_data):
        """Test successful book download."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.downloader.validate_book",
                    new_callable=AsyncMock,
                    return_value=True,
                ):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"Book downloaded successfully", b"")
                    )
                    mock_exec.return_value = mock_process

                    result = await download_book(book)

                    assert result is True

    async def test_download_book_calls_audible_cli(self, sample_book_data):
        """Test that download_book calls audible CLI."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.downloader.validate_book",
                    new_callable=AsyncMock,
                    return_value=True,
                ):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"Downloaded", b"")
                    )
                    mock_exec.return_value = mock_process

                    await download_book(book)

                    mock_exec.assert_called_once()
                    call_args = mock_exec.call_args[0]
                    assert "audible" in call_args
                    assert "download" in call_args

    async def test_download_book_with_asin(self, sample_book_data):
        """Test that download_book includes ASIN in command."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.downloader.validate_book",
                    new_callable=AsyncMock,
                    return_value=True,
                ):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"Downloaded", b"")
                    )
                    mock_exec.return_value = mock_process

                    await download_book(book)

                    call_args = mock_exec.call_args[0]
                    assert sample_book_data["asin"] in call_args

    async def test_download_book_validates_after_download(self, sample_book_data):
        """Test that download_book validates book after download."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.downloader.validate_book",
                    new_callable=AsyncMock,
                    return_value=True,
                ) as mock_validate:
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"Downloaded", b"")
                    )
                    mock_exec.return_value = mock_process

                    await download_book(book)

                    mock_validate.assert_called_once_with(book)

    async def test_download_book_validation_fails(self, sample_book_data):
        """Test download_book returns False when validation fails."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.downloader.validate_book",
                    new_callable=AsyncMock,
                    return_value=False,
                ):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"Downloaded", b"")
                    )
                    mock_exec.return_value = mock_process

                    result = await download_book(book)

                    assert result is False

    async def test_download_book_process_failure(self, sample_book_data):
        """Test download_book handles process failure."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch("src.operations.downloader.logger.error"):
                    mock_process = AsyncMock()
                    mock_process.returncode = 1
                    mock_process.communicate = AsyncMock(
                        return_value=(b"", b"Download failed")
                    )
                    mock_exec.return_value = mock_process

                    result = await download_book(book)

                    assert result is False

    async def test_download_book_no_new_files(self, sample_book_data):
        """Test download_book when no new files downloaded."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch("src.operations.downloader.logger.error"):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"No new files downloaded", b"")
                    )
                    mock_exec.return_value = mock_process

                    result = await download_book(book)

                    assert result is False

    async def test_download_book_timeout_error(self, sample_book_data):
        """Test download_book handles timeout."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch("src.operations.downloader.logger.error"):
                    mock_exec.side_effect = asyncio.TimeoutError()

                    result = await download_book(book)

                    assert result is False

    async def test_download_book_general_exception(self, sample_book_data):
        """Test download_book handles general exceptions."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ) as mock_ensure:
            with patch("src.operations.downloader.logger.error"):
                mock_ensure.side_effect = Exception("Directory error")

                result = await download_book(book)

                assert result is False

    async def test_download_book_ensures_directory(self, sample_book_data):
        """Test that download_book ensures directory exists."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ) as mock_ensure:
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.downloader.validate_book",
                    new_callable=AsyncMock,
                    return_value=True,
                ):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"Downloaded", b"")
                    )
                    mock_exec.return_value = mock_process

                    await download_book(book)

                    mock_ensure.assert_called_once()

    async def test_download_book_asx_fallback_flag(self, sample_book_data):
        """Test that download_book includes aax-fallback flag."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.downloader.validate_book",
                    new_callable=AsyncMock,
                    return_value=True,
                ):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"Downloaded", b"")
                    )
                    mock_exec.return_value = mock_process

                    await download_book(book)

                    call_args = mock_exec.call_args[0]
                    assert "--aax-fallback" in call_args

    async def test_download_book_format_flag(self, sample_book_data):
        """Test that download_book includes format flag."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.ensure_directory", new_callable=AsyncMock
        ):
            with patch(
                "src.operations.downloader.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.downloader.validate_book",
                    new_callable=AsyncMock,
                    return_value=True,
                ):
                    mock_process = AsyncMock()
                    mock_process.returncode = 0
                    mock_process.communicate = AsyncMock(
                        return_value=(b"Downloaded", b"")
                    )
                    mock_exec.return_value = mock_process

                    await download_book(book)

                    call_args = mock_exec.call_args[0]
                    assert "asin_ascii" in call_args


@pytest.mark.asyncio
@pytest.mark.unit
class TestValidateBook:
    """Test book validation functionality."""

    async def test_validate_book_exists_by_asin(self, sample_book_data):
        """Test validate_book with file found by ASIN."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.file_exists_in_directory", return_value=True
        ):
            result = await validate_book(book)

            assert result is True

    async def test_validate_book_not_exists(self, sample_book_data):
        """Test validate_book when file not found."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.file_exists_in_directory", return_value=False
        ):
            result = await validate_book(book)

            assert result is False

    async def test_validate_book_checks_identifiers(self, sample_book_data):
        """Test that validate_book checks with both ASIN and title."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.downloader.file_exists_in_directory") as mock_check:
            mock_check.return_value = True
            await validate_book(book)

            mock_check.assert_called_once()
            call_args = mock_check.call_args[0]
            identifiers = call_args[1]
            assert sample_book_data["asin"] in identifiers

    async def test_validate_book_normalizes_title(self, sample_book_data):
        """Test that validate_book normalizes title."""
        book = [sample_book_data["asin"], "Test-AudioBook!@#"]

        with patch("src.operations.downloader.file_exists_in_directory") as mock_check:
            with patch(
                "src.operations.downloader.normalize_filename",
                return_value="testaudiobook",
            ):
                mock_check.return_value = True
                await validate_book(book)

                call_args = mock_check.call_args[0]
                identifiers = call_args[1]
                assert "testaudiobook" in identifiers

    async def test_validate_book_logs_success(self, sample_book_data):
        """Test that validate_book logs when file exists."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.downloader.file_exists_in_directory", return_value=True
        ):
            with patch("src.operations.downloader.logger.info") as mock_logger:
                await validate_book(book)

                mock_logger.assert_called()

    async def test_validate_book_uses_download_dir(self, sample_book_data):
        """Test that validate_book uses DOWNLOAD_DIR config."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.downloader.file_exists_in_directory") as mock_check:
            with patch("src.operations.downloader.Config.DOWNLOAD_DIR", "/test/dir"):
                mock_check.return_value = True
                await validate_book(book)

                call_args = mock_check.call_args[0]
                assert call_args[0] == "/test/dir"
