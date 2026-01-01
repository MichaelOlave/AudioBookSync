"""Tests for MinIOClient wrapper."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from minio.error import S3Error

from src.infrastructure.minio_client import MinIOClient


@pytest.fixture
def mock_minio_client():
    """Mock Minio client for testing."""
    with patch("src.infrastructure.minio_client.Minio") as mock_minio:
        mock_instance = MagicMock()
        mock_minio.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def minio_client(mock_minio_client):
    """Create MinIOClient instance with mocked Minio client."""
    client = MinIOClient()
    client.client = mock_minio_client
    return client


@pytest.mark.unit
class TestMinIOClientBucketOperations:
    """Test bucket management operations."""

    def test_bucket_creation_and_existence(self, minio_client, mock_minio_client):
        """Test bucket creation and existence checking."""
        # Test bucket_exists returns False initially
        mock_minio_client.bucket_exists.return_value = False
        assert not minio_client.bucket_exists("user-123")
        mock_minio_client.bucket_exists.assert_called_once_with("user-123")

        # Test create_bucket creates new bucket
        mock_minio_client.bucket_exists.return_value = False
        result = minio_client.create_bucket("user-123")
        assert result is True
        mock_minio_client.make_bucket.assert_called_once_with("user-123")

        # Test bucket_exists returns True after creation
        mock_minio_client.bucket_exists.return_value = True
        assert minio_client.bucket_exists("user-123")

    def test_create_bucket_already_owned_by_you(self, minio_client, mock_minio_client):
        """Test create_bucket handles AlreadyOwnedByYou exception gracefully."""
        # Mock make_bucket to raise AlreadyOwnedByYou error
        error = S3Error(
            code="BucketAlreadyOwnedByYou",
            message="Bucket already owned by you",
            resource="/user-123",
            request_id="test-request-id",
            host_id="test-host-id",
            response=MagicMock(),
        )
        mock_minio_client.make_bucket.side_effect = error

        # Should return True (gracefully handle existing bucket)
        result = minio_client.create_bucket("user-123")
        assert result is True


@pytest.mark.unit
class TestMinIOClientFileUpload:
    """Test file upload operations with checksum verification."""

    def test_file_upload_with_checksum_verification(
        self, minio_client, mock_minio_client, temp_dir
    ):
        """Test file upload calculates checksum and verifies after upload."""
        # Create test file
        test_file = temp_dir / "test_book.aax"
        test_content = b"Test audiobook content for checksum verification"
        test_file.write_bytes(test_content)

        # Calculate expected SHA256
        expected_sha256 = hashlib.sha256(test_content).hexdigest()
        file_size = len(test_content)

        # Mock successful upload
        mock_minio_client.fput_object.return_value = MagicMock(etag="test-etag")

        # Mock stat_object to return metadata for verification
        mock_stat = MagicMock()
        mock_stat.size = file_size
        mock_stat.etag = "test-etag"
        mock_stat.content_type = "audio/aax"
        mock_minio_client.stat_object.return_value = mock_stat

        # Upload file
        result = minio_client.upload_file(
            str(test_file), "user-123", "downloaded/B001ABC123.aax"
        )

        # Verify upload was called
        assert result is True
        mock_minio_client.fput_object.assert_called_once()
        call_args = mock_minio_client.fput_object.call_args
        assert call_args[0][0] == "user-123"
        assert call_args[0][1] == "downloaded/B001ABC123.aax"
        assert call_args[0][2] == str(test_file)

        # Verify metadata was retrieved for verification
        mock_minio_client.stat_object.assert_called_once_with(
            "user-123", "downloaded/B001ABC123.aax"
        )

    def test_upload_with_retry_logic(self, minio_client, mock_minio_client, temp_dir):
        """Test upload retry logic with exponential backoff."""
        # Create test file
        test_file = temp_dir / "test_book.aax"
        test_file.write_bytes(b"Test content")

        # Mock first two attempts fail, third succeeds
        mock_stat = MagicMock()
        mock_stat.size = len(b"Test content")
        mock_stat.etag = "test-etag"
        mock_stat.content_type = "audio/aax"

        mock_minio_client.fput_object.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            MagicMock(etag="test-etag"),
        ]
        mock_minio_client.stat_object.return_value = mock_stat

        # Mock time.sleep to verify delays
        with patch("src.infrastructure.minio_client.time.sleep") as mock_sleep:
            result = minio_client.upload_file(
                str(test_file), "user-123", "downloaded/test.aax"
            )

            # Should succeed after retries
            assert result is True

            # Verify fput_object was called 3 times
            assert mock_minio_client.fput_object.call_count == 3

            # Verify exponential backoff delays: 1s, 2s
            assert mock_sleep.call_count == 2
            mock_sleep.assert_has_calls([call(1), call(2)])

    def test_upload_failure_after_max_retries(
        self, minio_client, mock_minio_client, temp_dir
    ):
        """Test upload returns False after exhausting all retries."""
        # Create test file
        test_file = temp_dir / "test_book.aax"
        test_file.write_bytes(b"Test content")

        # Mock all attempts fail
        mock_minio_client.fput_object.side_effect = Exception("Persistent error")

        # Mock time.sleep
        with patch("src.infrastructure.minio_client.time.sleep"):
            result = minio_client.upload_file(
                str(test_file), "user-123", "downloaded/test.aax"
            )

            # Should fail after all retries
            assert result is False

            # Verify fput_object was called 3 times
            assert mock_minio_client.fput_object.call_count == 3


@pytest.mark.unit
class TestMinIOClientFileDownload:
    """Test file download operations."""

    def test_file_download(self, minio_client, mock_minio_client, temp_dir):
        """Test downloading file from MinIO to local filesystem."""
        destination = temp_dir / "downloaded_book.m4b"

        # Mock successful download
        mock_minio_client.fget_object.return_value = MagicMock()

        # Download file
        result = minio_client.download_file(
            "user-123", "decrypted/test_book.m4b", str(destination)
        )

        # Verify download was successful
        assert result is True
        mock_minio_client.fget_object.assert_called_once_with(
            "user-123", "decrypted/test_book.m4b", str(destination)
        )

    def test_download_missing_file(self, minio_client, mock_minio_client, temp_dir):
        """Test download handles missing files gracefully."""
        destination = temp_dir / "missing_book.m4b"

        # Mock NoSuchKey error
        error = S3Error(
            code="NoSuchKey",
            message="The specified key does not exist",
            resource="/user-123/decrypted/missing.m4b",
            request_id="test-request-id",
            host_id="test-host-id",
            response=MagicMock(),
        )
        mock_minio_client.fget_object.side_effect = error

        # Download should return False
        result = minio_client.download_file(
            "user-123", "decrypted/missing.m4b", str(destination)
        )
        assert result is False


@pytest.mark.unit
class TestMinIOClientFileStreaming:
    """Test file streaming operations with Range support."""

    def test_file_streaming_with_range(self, minio_client, mock_minio_client):
        """Test streaming file with offset and length (HTTP Range)."""
        # Mock streaming response
        mock_response = MagicMock()
        test_data = b"Partial audiobook content chunk"
        mock_response.read.return_value = test_data
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_minio_client.get_object.return_value = mock_response

        # Stream file with Range parameters
        result = minio_client.stream_file(
            "user-123", "decrypted/audiobook.m4b", offset=1024, length=8192
        )

        # Verify streaming was called with correct parameters
        assert result == test_data
        mock_minio_client.get_object.assert_called_once_with(
            "user-123", "decrypted/audiobook.m4b", offset=1024, length=8192
        )

    def test_stream_full_file_without_range(self, minio_client, mock_minio_client):
        """Test streaming entire file without Range parameters."""
        # Mock streaming response
        mock_response = MagicMock()
        test_data = b"Full audiobook content"
        mock_response.read.return_value = test_data
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_minio_client.get_object.return_value = mock_response

        # Stream file without offset/length
        result = minio_client.stream_file("user-123", "decrypted/audiobook.m4b")

        # Verify streaming was called with defaults
        assert result == test_data
        mock_minio_client.get_object.assert_called_once_with(
            "user-123", "decrypted/audiobook.m4b", offset=0, length=None
        )


@pytest.mark.unit
class TestMinIOClientFileMetadata:
    """Test file metadata and deletion operations."""

    def test_get_file_metadata(self, minio_client, mock_minio_client):
        """Test retrieving file metadata."""
        # Mock stat_object response
        mock_stat = MagicMock()
        mock_stat.size = 1024000
        mock_stat.etag = "abc123def456"
        mock_stat.content_type = "audio/mp4"
        mock_stat.last_modified = "2024-01-01T12:00:00Z"
        mock_minio_client.stat_object.return_value = mock_stat

        # Get metadata
        metadata = minio_client.get_file_metadata("user-123", "decrypted/book.m4b")

        # Verify metadata structure
        assert metadata is not None
        assert metadata["size"] == 1024000
        assert metadata["etag"] == "abc123def456"
        assert metadata["content_type"] == "audio/mp4"
        assert metadata["last_modified"] == "2024-01-01T12:00:00Z"

        mock_minio_client.stat_object.assert_called_once_with(
            "user-123", "decrypted/book.m4b"
        )

    def test_get_metadata_missing_file(self, minio_client, mock_minio_client):
        """Test get_file_metadata returns None for missing files."""
        # Mock NoSuchKey error
        error = S3Error(
            code="NoSuchKey",
            message="The specified key does not exist",
            resource="/user-123/missing.m4b",
            request_id="test-request-id",
            host_id="test-host-id",
            response=MagicMock(),
        )
        mock_minio_client.stat_object.side_effect = error

        # Get metadata should return None
        metadata = minio_client.get_file_metadata("user-123", "missing.m4b")
        assert metadata is None

    def test_file_exists(self, minio_client, mock_minio_client):
        """Test checking if file exists."""
        # Mock stat_object success
        mock_minio_client.stat_object.return_value = MagicMock()

        # File should exist
        assert minio_client.file_exists("user-123", "decrypted/book.m4b") is True

        # Mock NoSuchKey error for missing file
        error = S3Error(
            code="NoSuchKey",
            message="Not found",
            resource="/user-123/missing.m4b",
            request_id="test-request-id",
            host_id="test-host-id",
            response=MagicMock(),
        )
        mock_minio_client.stat_object.side_effect = error

        # File should not exist
        assert minio_client.file_exists("user-123", "missing.m4b") is False

    def test_file_deletion(self, minio_client, mock_minio_client):
        """Test deleting file from MinIO."""
        # Mock successful deletion
        mock_minio_client.remove_object.return_value = None

        # Delete file
        result = minio_client.delete_file("user-123", "decrypted/old_book.m4b")

        # Verify deletion was successful
        assert result is True
        mock_minio_client.remove_object.assert_called_once_with(
            "user-123", "decrypted/old_book.m4b"
        )

    def test_delete_missing_file(self, minio_client, mock_minio_client):
        """Test deleting non-existent file returns True (idempotent)."""
        # Mock NoSuchKey error
        error = S3Error(
            code="NoSuchKey",
            message="Not found",
            resource="/user-123/missing.m4b",
            request_id="test-request-id",
            host_id="test-host-id",
            response=MagicMock(),
        )
        mock_minio_client.remove_object.side_effect = error

        # Delete should return True (idempotent operation)
        result = minio_client.delete_file("user-123", "missing.m4b")
        assert result is True
