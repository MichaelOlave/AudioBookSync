"""Tests for src.operations.decryptor module."""

from unittest.mock import AsyncMock, patch

import pytest

from src.operations.decryptor import decrypt_book, validate_decrypted_book


@pytest.mark.asyncio
@pytest.mark.unit
class TestDecryptBook:
    """Test book decryption functionality."""

    async def test_decrypt_book_success(self, sample_book_data):
        """Test successful book decryption."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor.validate_decrypted_book",
                        new_callable=AsyncMock,
                        return_value=True,
                    ):
                        mock_process = AsyncMock()
                        mock_process.returncode = 0
                        mock_process.communicate = AsyncMock(
                            return_value=(b"Conversion complete", b"")
                        )
                        mock_exec.return_value = mock_process

                        result = await decrypt_book(book)

                        assert result is True

    async def test_decrypt_book_calls_ffmpeg(self, sample_book_data):
        """Test that decrypt_book calls ffmpeg."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor.validate_decrypted_book",
                        new_callable=AsyncMock,
                        return_value=True,
                    ):
                        mock_process = AsyncMock()
                        mock_process.returncode = 0
                        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                        mock_exec.return_value = mock_process

                        await decrypt_book(book)

                        mock_exec.assert_called_once()
                        call_args = mock_exec.call_args[0]
                        assert "ffmpeg" in call_args

    async def test_decrypt_book_uses_activation_bytes(self, sample_book_data):
        """Test that decrypt_book includes activation bytes."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor.validate_decrypted_book",
                        new_callable=AsyncMock,
                        return_value=True,
                    ):
                        with patch(
                            "src.operations.decryptor.Config.ACTIVATION_BYTES",
                            "test_bytes",
                        ):
                            mock_process = AsyncMock()
                            mock_process.returncode = 0
                            mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                            mock_exec.return_value = mock_process

                            await decrypt_book(book)

                            call_args = mock_exec.call_args[0]
                            assert "test_bytes" in call_args

    async def test_decrypt_book_validates_after_decrypt(self, sample_book_data):
        """Test that decrypt_book validates after decryption."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor.validate_decrypted_book",
                        new_callable=AsyncMock,
                        return_value=True,
                    ) as mock_validate:
                        mock_process = AsyncMock()
                        mock_process.returncode = 0
                        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                        mock_exec.return_value = mock_process

                        await decrypt_book(book)

                        mock_validate.assert_called_once_with(book)

    async def test_decrypt_book_validation_fails(self, sample_book_data):
        """Test decrypt_book returns False when validation fails."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor.validate_decrypted_book",
                        new_callable=AsyncMock,
                        return_value=False,
                    ):
                        with patch("src.operations.decryptor.logger.error"):
                            mock_process = AsyncMock()
                            mock_process.returncode = 0
                            mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                            mock_exec.return_value = mock_process

                            result = await decrypt_book(book)

                            assert result is False

    async def test_decrypt_book_ffmpeg_error(self, sample_book_data):
        """Test decrypt_book handles ffmpeg errors."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch("src.operations.decryptor.logger.error"):
                        mock_process = AsyncMock()
                        mock_process.returncode = 1
                        mock_process.communicate = AsyncMock(return_value=(b"", b"FFmpeg error"))
                        mock_exec.return_value = mock_process

                        result = await decrypt_book(book)

                        assert result is False

    async def test_decrypt_book_file_not_found(self, sample_book_data):
        """Test decrypt_book when no matching file found."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch("src.operations.decryptor.os.listdir", return_value=["other_file.aax"]):
                with patch("src.operations.decryptor.logger.error"):
                    result = await decrypt_book(book)

                    assert result is False

    async def test_decrypt_book_no_files_in_download_dir(self, sample_book_data):
        """Test decrypt_book when download directory is empty."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch("src.operations.decryptor.os.listdir", return_value=[]):
                with patch("src.operations.decryptor.logger.error"):
                    result = await decrypt_book(book)

                    assert result is False

    async def test_decrypt_book_normalizes_title(self, sample_book_data):
        """Test that decrypt_book normalizes title."""
        book = [sample_book_data["asin"], "Test-AudioBook!@#"]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.normalize_filename",
                    return_value="testaudiobook",
                ):
                    with patch(
                        "src.operations.decryptor.asyncio.create_subprocess_exec",
                        new_callable=AsyncMock,
                    ) as mock_exec:
                        with patch(
                            "src.operations.decryptor.validate_decrypted_book",
                            new_callable=AsyncMock,
                            return_value=True,
                        ):
                            mock_process = AsyncMock()
                            mock_process.returncode = 0
                            mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                            mock_exec.return_value = mock_process

                            await decrypt_book(book)

                            call_args = mock_exec.call_args[0]
                            assert "testaudiobook" in call_args

    async def test_decrypt_book_ensures_directory(self, sample_book_data):
        """Test that decrypt_book ensures directory exists."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch(
            "src.operations.decryptor.ensure_directory", new_callable=AsyncMock
        ) as mock_ensure:
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor.validate_decrypted_book",
                        new_callable=AsyncMock,
                        return_value=True,
                    ):
                        mock_process = AsyncMock()
                        mock_process.returncode = 0
                        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                        mock_exec.return_value = mock_process

                        await decrypt_book(book)

                        mock_ensure.assert_called_once()

    async def test_decrypt_book_ffmpeg_copy_codec(self, sample_book_data):
        """Test that decrypt_book uses copy codec."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor.validate_decrypted_book",
                        new_callable=AsyncMock,
                        return_value=True,
                    ):
                        mock_process = AsyncMock()
                        mock_process.returncode = 0
                        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                        mock_exec.return_value = mock_process

                        await decrypt_book(book)

                        call_args = mock_exec.call_args[0]
                        assert "copy" in call_args

    async def test_decrypt_book_output_extension(self, sample_book_data):
        """Test that decrypt_book outputs m4b format."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.ensure_directory", new_callable=AsyncMock):
            with patch(
                "src.operations.decryptor.os.listdir",
                return_value=[f"{sample_book_data['asin']}.aax"],
            ):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor.validate_decrypted_book",
                        new_callable=AsyncMock,
                        return_value=True,
                    ):
                        with patch(
                            "src.operations.decryptor.normalize_filename",
                            return_value="test_title",
                        ):
                            mock_process = AsyncMock()
                            mock_process.returncode = 0
                            mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                            mock_exec.return_value = mock_process

                            await decrypt_book(book)

                            call_args = mock_exec.call_args[0]
                            output_path = [arg for arg in call_args if ".m4b" in str(arg)]
                            assert len(output_path) > 0


@pytest.mark.asyncio
@pytest.mark.unit
class TestValidateDecryptedBook:
    """Test decrypted book validation functionality."""

    async def test_validate_decrypted_book_exists(self, sample_book_data):
        """Test validate_decrypted_book when file exists."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.file_exists_in_directory", return_value=True):
            result = await validate_decrypted_book(book)

            assert result is True

    async def test_validate_decrypted_book_not_exists(self, sample_book_data):
        """Test validate_decrypted_book when file not found."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.file_exists_in_directory", return_value=False):
            result = await validate_decrypted_book(book)

            assert result is False

    async def test_validate_decrypted_book_checks_identifiers(self, sample_book_data):
        """Test that validate_decrypted_book checks with both ASIN and title."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.file_exists_in_directory") as mock_check:
            mock_check.return_value = True
            await validate_decrypted_book(book)

            mock_check.assert_called_once()
            call_args = mock_check.call_args[0]
            identifiers = call_args[1]
            assert sample_book_data["asin"] in identifiers

    async def test_validate_decrypted_book_normalizes_title(self, sample_book_data):
        """Test that validate_decrypted_book normalizes title."""
        book = [sample_book_data["asin"], "Test-AudioBook!@#"]

        with patch("src.operations.decryptor.file_exists_in_directory") as mock_check:
            with patch(
                "src.operations.decryptor.normalize_filename",
                return_value="testaudiobook",
            ):
                mock_check.return_value = True
                await validate_decrypted_book(book)

                call_args = mock_check.call_args[0]
                identifiers = call_args[1]
                assert "testaudiobook" in identifiers

    async def test_validate_decrypted_book_logs_success(self, sample_book_data):
        """Test that validate_decrypted_book logs success."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.file_exists_in_directory", return_value=True):
            with patch("src.operations.decryptor.logger.info") as mock_logger:
                await validate_decrypted_book(book)

                mock_logger.assert_called()

    async def test_validate_decrypted_book_uses_decrypted_dir(self, sample_book_data):
        """Test that validate_decrypted_book uses DECRYPTED_DIR config."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        with patch("src.operations.decryptor.file_exists_in_directory") as mock_check:
            with patch("src.operations.decryptor.Config.DECRYPTED_DIR", "/test/decrypted"):
                mock_check.return_value = True
                await validate_decrypted_book(book)

                call_args = mock_check.call_args[0]
                assert call_args[0] == "/test/decrypted"
