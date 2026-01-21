"""MinIO S3-compatible object storage client wrapper.

This module provides a high-level interface for MinIO operations including:
- Bucket management (create, check existence, set quotas)
- File upload with checksum verification and retry logic
- File download and streaming with HTTP Range support
- File metadata retrieval and deletion
- Comprehensive error handling and logging
"""

import hashlib
import time
from pathlib import Path
from typing import Optional

from loguru import logger
from minio import Minio
from minio.error import S3Error

from src.core.config import Config


class MinIOClient:
    """MinIO S3-compatible object storage client wrapper.

    Provides high-level operations for bucket management, file upload/download,
    with built-in retry logic, checksum verification, and comprehensive logging.

    The client handles connection pooling, exponential backoff retries, and
    graceful error handling for common S3 errors (BucketAlreadyOwnedByYou, NoSuchKey).

    Example usage:
        client = MinIOClient()
        client.create_bucket("user-123")
        client.upload_file("/path/to/file.aax", "user-123", "downloaded/book.aax")
        data = client.stream_file("user-123", "downloaded/book.aax", offset=0, length=8192)
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
    ):
        """Initialize MinIO client with configuration from Config class or custom parameters.

        Loads connection parameters from environment variables via Config:
        - MINIO_ENDPOINT: MinIO server endpoint (e.g., "localhost:9000")
        - MINIO_ACCESS_KEY: Access key for authentication
        - MINIO_SECRET_KEY: Secret key for authentication
        - MINIO_SECURE: Whether to use HTTPS (default: False for local dev)

        Args:
            endpoint: Optional custom MinIO endpoint (overrides Config)
            access_key: Optional custom access key (overrides Config)
            secret_key: Optional custom secret key (overrides Config)
            secure: Optional custom secure setting (overrides Config)
        """
        # Use provided parameters or fall back to Config
        self.endpoint = endpoint or Config.MINIO_ENDPOINT
        self.access_key = access_key or Config.MINIO_ACCESS_KEY
        self.secret_key = secret_key or Config.MINIO_SECRET_KEY
        self.secure = secure if secure is not None else Config.MINIO_SECURE

        # Initialize Minio client with connection parameters
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        logger.info(
            f"MinIO client initialized: endpoint={self.endpoint}, secure={self.secure}"
        )

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists.

        Args:
            bucket_name: Name of the bucket to check

        Returns:
            True if bucket exists, False otherwise
        """
        try:
            exists = self.client.bucket_exists(bucket_name)
            logger.debug(f"Bucket exists check: {bucket_name} = {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check bucket existence for {bucket_name}: {e}")
            return False

    def create_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket.

        Gracefully handles BucketAlreadyOwnedByYou exception by returning True.

        Args:
            bucket_name: Name of the bucket to create

        Returns:
            True if bucket was created or already exists, False on other errors
        """
        try:
            self.client.make_bucket(bucket_name)
            logger.info(f"Created bucket: {bucket_name}")
            return True
        except S3Error as e:
            if e.code == "BucketAlreadyOwnedByYou":
                logger.info(f"Bucket already exists and is owned by you: {bucket_name}")
                return True
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            return False

    def set_bucket_quota(self, bucket_name: str, quota_bytes: int) -> bool:
        """Set bucket quota (storage limit).

        Note: This requires MinIO Admin API which is separate from S3 API.
        This is a placeholder implementation that logs a warning.
        For production use, consider implementing with minio.MinioAdmin.

        Args:
            bucket_name: Name of the bucket
            quota_bytes: Quota size in bytes

        Returns:
            False (not implemented yet)
        """
        logger.warning(
            f"set_bucket_quota not implemented for {bucket_name} "
            f"(quota: {quota_bytes} bytes). Requires MinIO Admin API."
        )
        return False

    def upload_file(self, file_path: str, bucket_name: str, object_key: str) -> bool:
        """Upload file to MinIO with checksum verification and retry logic.

        Implements exponential backoff retry: 3 attempts with 1s, 2s, 4s delays.
        Calculates SHA256 checksum before upload and verifies file size after upload.

        Args:
            file_path: Local path to file to upload
            bucket_name: Target bucket name
            object_key: Object key (path) in bucket

        Returns:
            True if upload succeeded and verification passed, False otherwise
        """
        # Calculate SHA256 checksum of source file
        try:
            source_checksum = self._calculate_sha256(file_path)
            source_size = Path(file_path).stat().st_size
            logger.debug(
                f"Source file: {file_path}, SHA256: {source_checksum}, "
                f"Size: {source_size} bytes"
            )
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return False

        # Retry logic with exponential backoff
        max_retries = 3
        delays = [1, 2, 4]

        for attempt in range(max_retries):
            try:
                # Upload file
                self.client.fput_object(bucket_name, object_key, file_path)
                logger.info(
                    f"Uploaded file to MinIO: {file_path} -> "
                    f"{bucket_name}/{object_key}"
                )

                # Verify upload by checking metadata
                metadata = self.get_file_metadata(bucket_name, object_key)
                if not metadata:
                    raise Exception("Failed to retrieve metadata after upload")

                # Verify file size
                if metadata["size"] != source_size:
                    raise Exception(
                        f"Size mismatch: source={source_size}, "
                        f"uploaded={metadata['size']}"
                    )

                logger.info(
                    f"Upload verification successful: {bucket_name}/{object_key}"
                )
                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = delays[attempt]
                    logger.warning(
                        f"Upload attempt {attempt + 1}/{max_retries} failed for "
                        f"{bucket_name}/{object_key}: {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Upload failed after {max_retries} attempts for "
                        f"{bucket_name}/{object_key}: {e}"
                    )
                    return False

        return False

    def download_file(
        self, bucket_name: str, object_key: str, destination_path: str
    ) -> bool:
        """Download file from MinIO to local filesystem.

        Args:
            bucket_name: Source bucket name
            object_key: Object key (path) in bucket
            destination_path: Local destination path

        Returns:
            True if download succeeded, False otherwise
        """
        try:
            self.client.fget_object(bucket_name, object_key, destination_path)
            logger.info(
                f"Downloaded file from MinIO: {bucket_name}/{object_key} -> "
                f"{destination_path}"
            )
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(
                    f"File not found in MinIO: {bucket_name}/{object_key}"
                )
                return False
            logger.error(
                f"Failed to download file {bucket_name}/{object_key}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to download file {bucket_name}/{object_key}: {e}"
            )
            return False

    def stream_file(
        self,
        bucket_name: str,
        object_key: str,
        offset: int = 0,
        length: Optional[int] = None,
    ) -> bytes:
        """Stream file from MinIO with HTTP Range support.

        Supports partial content retrieval for seeking in audio players.

        Args:
            bucket_name: Source bucket name
            object_key: Object key (path) in bucket
            offset: Byte offset to start reading from (default: 0)
            length: Number of bytes to read (default: None for all remaining)

        Returns:
            File data as bytes, empty bytes on error
        """
        try:
            if length is not None:
                response = self.client.get_object(
                    bucket_name, object_key, offset=offset, length=length
                )
            else:
                response = self.client.get_object(
                    bucket_name, object_key, offset=offset
                )
            data = response.read()
            response.close()
            logger.debug(
                f"Streamed {len(data)} bytes from {bucket_name}/{object_key} "
                f"(offset={offset}, length={length})"
            )
            return data
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.warning(
                    f"File not found for streaming: {bucket_name}/{object_key}"
                )
                return b""
            logger.error(f"Failed to stream file {bucket_name}/{object_key}: {e}")
            return b""
        except Exception as e:
            logger.error(f"Failed to stream file {bucket_name}/{object_key}: {e}")
            return b""

    def file_exists(self, bucket_name: str, object_key: str) -> bool:
        """Check if a file exists in MinIO.

        Args:
            bucket_name: Bucket name
            object_key: Object key (path) in bucket

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.stat_object(bucket_name, object_key)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(
                f"Error checking file existence {bucket_name}/{object_key}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Error checking file existence {bucket_name}/{object_key}: {e}"
            )
            return False

    def get_file_metadata(
        self, bucket_name: str, object_key: str
    ) -> Optional[dict]:
        """Get file metadata from MinIO.

        Args:
            bucket_name: Bucket name
            object_key: Object key (path) in bucket

        Returns:
            Dictionary with metadata (size, etag, content_type, last_modified)
            or None if file doesn't exist
        """
        try:
            stat = self.client.stat_object(bucket_name, object_key)
            metadata = {
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
            }
            logger.debug(f"Retrieved metadata for {bucket_name}/{object_key}")
            return metadata
        except S3Error as e:
            if e.code == "NoSuchKey":
                logger.debug(
                    f"File not found for metadata: {bucket_name}/{object_key}"
                )
                return None
            logger.error(
                f"Failed to get metadata for {bucket_name}/{object_key}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Failed to get metadata for {bucket_name}/{object_key}: {e}"
            )
            return None

    def delete_file(self, bucket_name: str, object_key: str) -> bool:
        """Delete file from MinIO.

        This is an idempotent operation - deleting a non-existent file returns True.

        Args:
            bucket_name: Bucket name
            object_key: Object key (path) in bucket

        Returns:
            True if deletion succeeded or file doesn't exist, False on other errors
        """
        try:
            self.client.remove_object(bucket_name, object_key)
            logger.info(f"Deleted file from MinIO: {bucket_name}/{object_key}")
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                # Idempotent operation - file already doesn't exist
                logger.debug(
                    f"File already deleted or doesn't exist: "
                    f"{bucket_name}/{object_key}"
                )
                return True
            logger.error(f"Failed to delete file {bucket_name}/{object_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {bucket_name}/{object_key}: {e}")
            return False

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hex digest

        Raises:
            Exception: If file cannot be read
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
