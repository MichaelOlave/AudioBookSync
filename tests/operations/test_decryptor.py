"""Tests for src.operations.decryptor module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.operations.decryptor import decrypt_book, validate_decrypted_book


@pytest.mark.asyncio
@pytest.mark.unit
class TestDecryptBook:
    """Test book decryption functionality."""

    async def test_decrypt_book_success(self, sample_book_data):
        """Test successful book decryption."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        with patch("src.operations.decryptor.os.path.exists", return_value=True):
            with patch(
                "src.operations.decryptor.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                with patch(
                    "src.operations.decryptor._upload_decrypted_file_to_minio",
                    new_callable=AsyncMock,
                    return_value=(True, "decrypted/test.m4b"),
                ):
                    with patch(
                        "src.operations.decryptor._extract_chapters_from_file",
                        new_callable=AsyncMock,
                        return_value=[],
                    ):
                        with patch(
                            "src.operations.decryptor._store_chapters",
                            new_callable=AsyncMock,
                        ):
                            mock_process = AsyncMock()
                            mock_process.returncode = 0
                            mock_process.communicate = AsyncMock(
                                return_value=(b"Conversion complete", b"")
                            )
                            mock_exec.return_value = mock_process

                            result = await decrypt_book(
                                book,
                                user_id=user_id,
                                encrypted_file_path="/tmp/test.aax",
                                activation_bytes="test_bytes",
                            )

                            assert result is True
                            call_args = mock_exec.call_args[0]
                            assert "ffmpeg" in call_args
                            assert "test_bytes" in call_args

    async def test_decrypt_book_uses_normalized_title(self, sample_book_data):
        """Test that decrypt_book uses normalized title in output filename."""
        book = [sample_book_data["asin"], "Test-AudioBook!@#"]
        user_id = "user-123"

        with patch("src.operations.decryptor.normalize_filename", return_value="testaudiobook"):
            with patch("src.operations.decryptor.os.path.exists", return_value=True):
                with patch(
                    "src.operations.decryptor.asyncio.create_subprocess_exec",
                    new_callable=AsyncMock,
                ) as mock_exec:
                    with patch(
                        "src.operations.decryptor._upload_decrypted_file_to_minio",
                        new_callable=AsyncMock,
                        return_value=(True, "decrypted/testaudiobook.m4b"),
                    ) as mock_upload:
                        with patch(
                            "src.operations.decryptor._extract_chapters_from_file",
                            new_callable=AsyncMock,
                            return_value=[],
                        ):
                            with patch(
                                "src.operations.decryptor._store_chapters",
                                new_callable=AsyncMock,
                            ):
                                mock_process = AsyncMock()
                                mock_process.returncode = 0
                                mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
                                mock_exec.return_value = mock_process

                                await decrypt_book(
                                    book,
                                    user_id=user_id,
                                    encrypted_file_path="/tmp/test.aax",
                                    activation_bytes="test_bytes",
                                )

                                call_args = mock_exec.call_args[0]
                                output_paths = [
                                    arg for arg in call_args if "testaudiobook" in str(arg)
                                ]
                                assert output_paths
                                mock_upload.assert_called_once()
                                assert mock_upload.call_args[0][1] == "testaudiobook"

    async def test_decrypt_book_ffmpeg_error(self, sample_book_data):
        """Test decrypt_book handles ffmpeg errors."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        with patch("src.operations.decryptor.os.path.exists", return_value=True):
            with patch(
                "src.operations.decryptor.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec:
                mock_process = AsyncMock()
                mock_process.returncode = 1
                mock_process.communicate = AsyncMock(return_value=(b"", b"FFmpeg error"))
                mock_exec.return_value = mock_process

                result = await decrypt_book(
                    book,
                    user_id=user_id,
                    encrypted_file_path="/tmp/test.aax",
                    activation_bytes="test_bytes",
                )

                assert result is False

    async def test_decrypt_book_missing_encrypted_file(self, sample_book_data):
        """Test decrypt_book when encrypted file is missing."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        with patch("src.operations.decryptor.os.path.exists", return_value=False):
            result = await decrypt_book(
                book,
                user_id=user_id,
                encrypted_file_path="/tmp/missing.aax",
                activation_bytes="test_bytes",
            )

            assert result is False

    async def test_decrypt_book_requires_activation_bytes(self, sample_book_data):
        """Test decrypt_book returns False when activation bytes are missing."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        with patch("src.operations.decryptor.Config.ACTIVATION_BYTES", "bytes_go_here"):
            result = await decrypt_book(
                book,
                user_id=user_id,
                encrypted_file_path="/tmp/test.aax",
            )

            assert result is False

    async def test_decrypt_book_retry_requires_path(self, sample_book_data):
        """Test decrypt_book retry requires encrypted file path."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        result = await decrypt_book(
            book,
            user_id=user_id,
            encrypted_file_path=None,
            is_retry=True,
            activation_bytes="test_bytes",
        )

        assert result is False


@pytest.mark.asyncio
@pytest.mark.unit
class TestValidateDecryptedBook:
    """Test decrypted book validation functionality."""

    async def test_validate_decrypted_book_exists(self, sample_book_data):
        """Test validate_decrypted_book when file exists."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        mock_client = MagicMock()
        mock_client.file_exists.return_value = True
        mock_service = MagicMock()
        mock_service.minio_client = mock_client

        with patch("src.operations.decryptor.StorageService", return_value=mock_service):
            with patch("src.operations.decryptor.normalize_filename", return_value="testtitle"):
                result = await validate_decrypted_book(book, user_id=user_id)

                assert result is True
                mock_client.file_exists.assert_called_once_with(
                    "user-user-123",
                    "decrypted/testtitle.m4b",
                )

    async def test_validate_decrypted_book_not_exists(self, sample_book_data):
        """Test validate_decrypted_book when file not found."""
        book = [sample_book_data["asin"], sample_book_data["title"]]
        user_id = "user-123"

        mock_client = MagicMock()
        mock_client.file_exists.return_value = False
        mock_service = MagicMock()
        mock_service.minio_client = mock_client

        with patch("src.operations.decryptor.StorageService", return_value=mock_service):
            result = await validate_decrypted_book(book, user_id=user_id)

            assert result is False

    async def test_validate_decrypted_book_requires_user(self, sample_book_data):
        """Test validate_decrypted_book returns False without user_id."""
        book = [sample_book_data["asin"], sample_book_data["title"]]

        result = await validate_decrypted_book(book, user_id="")

        assert result is False
