"""Tests for StorageService abstraction layer."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.infrastructure.storage_service import StorageService


@pytest.fixture
def mock_minio_client():
    """Mock MinIOClient for testing."""
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False
    mock_client.create_bucket.return_value = True
    mock_client.upload_file.return_value = True
    mock_client.download_file.return_value = True
    mock_client.stream_file.return_value = b"test content"
    mock_client.delete_file.return_value = True
    return mock_client


@pytest.fixture
def storage_service(mock_minio_client):
    """Create StorageService instance with native MinIO."""
    service = StorageService(minio_client=mock_minio_client)
    return service


@pytest.mark.unit
class TestObjectKeyGeneration:
    """Test object key generation for different file types."""

    def test_generate_object_key_for_downloaded_files(self, storage_service):
        """Test object key generation follows pattern: downloaded/{asin}.aax"""
        service = storage_service

        # Generate object key for downloaded file
        object_key = service._generate_object_key(file_type="downloaded", asin="B001ABC123")

        # Verify pattern: downloaded/{asin}.aax
        assert object_key == "downloaded/B001ABC123.aax"

    def test_generate_object_key_for_decrypted_files(self, storage_service):
        """Test object key generation follows pattern: decrypted/{normalized_title}.m4b"""
        service = storage_service

        # Generate object key for decrypted file with special characters in title
        object_key = service._generate_object_key(
            file_type="decrypted", title="The Great Book: Volume 2 - Part One!"
        )

        # Verify pattern: decrypted/{normalized_title}.m4b
        # normalize_filename should remove special chars and convert to lowercase
        assert object_key.startswith("decrypted/")
        assert object_key.endswith(".m4b")
        # Should normalize title (exact normalization depends on normalize_filename implementation)
        assert ":" not in object_key
        assert "!" not in object_key

    def test_generate_object_key_validates_required_parameters(self, storage_service):
        """Test object key generation validates required parameters based on file_type."""
        service = storage_service

        # Downloaded files require asin
        with pytest.raises(ValueError, match="asin.*required"):
            service._generate_object_key(file_type="downloaded", title="Some Title")

        # Decrypted files require title
        with pytest.raises(ValueError, match="title.*required"):
            service._generate_object_key(file_type="decrypted", asin="B001ABC123")

        # Invalid file_type
        with pytest.raises(ValueError, match="file_type.*downloaded.*decrypted"):
            service._generate_object_key(file_type="invalid", asin="B001ABC123")


@pytest.mark.unit
class TestBucketManagement:
    """Test bucket creation and management."""

    def test_get_user_bucket_returns_correct_pattern(self, storage_service):
        """Test _get_user_bucket returns pattern: user-{user_id}"""
        service = storage_service

        # Get bucket name for user
        bucket_name = service._get_user_bucket("test-user-123")

        # Verify pattern: user-{user_id}
        assert bucket_name == "user-test-user-123"

    def test_ensure_user_bucket_creates_bucket_if_not_exists(
        self, storage_service, mock_minio_client
    ):
        """Test ensure_user_bucket creates bucket when it doesn't exist."""
        service = storage_service

        # Mock bucket doesn't exist
        mock_minio_client.bucket_exists.return_value = False
        mock_minio_client.create_bucket.return_value = True

        # Ensure bucket exists
        result = service.ensure_user_bucket("test-user-123")

        # Verify bucket was checked and created
        assert result is True
        mock_minio_client.bucket_exists.assert_called_once_with("user-test-user-123")
        mock_minio_client.create_bucket.assert_called_once_with("user-test-user-123")

    def test_ensure_user_bucket_returns_true_if_bucket_already_exists(
        self, storage_service, mock_minio_client
    ):
        """Test ensure_user_bucket returns True when bucket already exists."""
        service = storage_service

        # Mock bucket exists
        mock_minio_client.bucket_exists.return_value = True

        # Ensure bucket exists
        result = service.ensure_user_bucket("test-user-123")

        # Verify bucket existence was checked but not created
        assert result is True
        mock_minio_client.bucket_exists.assert_called_once_with("user-test-user-123")
        mock_minio_client.create_bucket.assert_not_called()


@pytest.mark.unit
class TestSaveFile:
    """Test save_file MinIO upload."""

    def test_save_file_uploads_to_minio_when_enabled(
        self, storage_service, mock_minio_client, temp_dir
    ):
        """Test save_file uploads to MinIO when USE_MINIO_STORAGE=True."""
        service = storage_service

        # Create test file
        test_file = temp_dir / "test_book.aax"
        test_file.write_bytes(b"Test audiobook content")

        # Mock bucket exists
        mock_minio_client.bucket_exists.return_value = True
        mock_minio_client.upload_file.return_value = True

        # Save file
        success, object_key = service.save_file(
            user_id="test-user-123",
            file_path=str(test_file),
            file_type="downloaded",
            asin="B001ABC123",
        )

        # Verify upload was successful
        assert success is True
        assert object_key == "downloaded/B001ABC123.aax"

        # Verify MinIO upload was called with correct parameters
        mock_minio_client.upload_file.assert_called_once_with(
            str(test_file), "user-test-user-123", "downloaded/B001ABC123.aax"
        )

    def test_save_file_returns_false_on_upload_failure(
        self, storage_service, mock_minio_client, temp_dir
    ):
        """Test save_file returns False when MinIO upload fails."""
        service = storage_service

        # Create test file
        test_file = temp_dir / "test_book.aax"
        test_file.write_bytes(b"Test audiobook content")

        # Mock bucket exists but upload fails
        mock_minio_client.bucket_exists.return_value = True
        mock_minio_client.upload_file.return_value = False

        # Save file
        success, object_key = service.save_file(
            user_id="test-user-123",
            file_path=str(test_file),
            file_type="downloaded",
            asin="B001ABC123",
        )

        # Verify operation failed
        assert success is False
        assert object_key is None


@pytest.mark.unit
class TestGetFile:
    """Test get_file MinIO download."""

    def test_get_file_downloads_from_minio_when_object_key_provided(
        self, storage_service, mock_minio_client, temp_dir
    ):
        """Test get_file downloads from MinIO when object_key is provided."""
        service = storage_service

        # Mock successful MinIO download
        def mock_download(bucket, object_key, dest_path):
            # Simulate MinIO downloading file to destination
            Path(dest_path).write_bytes(b"MinIO content")
            return True

        mock_minio_client.download_file.side_effect = mock_download

        # Get file from MinIO
        file_path = service.get_file(
            user_id="test-user-123", object_key="downloaded/B001ABC123.aax"
        )

        # Verify file path returned (should be temp location)
        assert file_path is not None
        assert Path(file_path).exists()
        assert Path(file_path).read_bytes() == b"MinIO content"
