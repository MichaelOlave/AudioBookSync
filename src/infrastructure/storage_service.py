"""Storage service abstraction layer for MinIO object storage.

This module provides a unified interface for MinIO object storage operations
with per-user bucket isolation. Native MinIO-only implementation with no
filesystem fallback.

Key features:
- Per-user bucket isolation: user-{user_id} bucket pattern
- HTTP Range request support for audio streaming
- Direct MinIO access (no dual-read pattern)
- Comprehensive error handling and logging
"""

import tempfile
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

from src.core.config import Config
from src.infrastructure.file_utils import normalize_filename
from src.infrastructure.minio_client import MinIOClient


class StorageService:
    """Storage service for MinIO object storage.

    Provides unified interface for MinIO object storage operations with per-user
    bucket isolation. Native MinIO-only implementation - no filesystem fallback.

    Example usage:
        service = StorageService()

        # Save file (uploads to MinIO)
        success, object_key = service.save_file(
            user_id="user-123",
            file_path="/path/to/book.aax",
            file_type="downloaded",
            asin="B001ABC123"
        )

        # Stream file with Range support
        chunk = service.stream_file(
            user_id="user-123",
            object_key="decrypted/audiobook.m4b",
            offset=1024,
            length=8192
        )
    """

    def __init__(self, minio_client: Optional[MinIOClient] = None):
        """Initialize StorageService with MinIOClient.

        Args:
            minio_client: MinIOClient instance for testing (dependency injection).
                         If None, creates new instance.

        MinIO is always enabled in native storage mode.
        """
        self.minio_client = minio_client if minio_client else MinIOClient()
        logger.info("StorageService initialized with MinIO")

    def _generate_object_key(
        self, file_type: str, asin: Optional[str] = None, title: Optional[str] = None
    ) -> str:
        """Generate object key for MinIO storage.

        Object key patterns:
        - Downloaded files: "downloaded/{asin}.aax"
        - Decrypted files: "decrypted/{normalized_title}.m4b"

        Args:
            file_type: Either "downloaded" or "decrypted"
            asin: ASIN for downloaded files (required when file_type="downloaded")
            title: Book title for decrypted files (required when file_type="decrypted")

        Returns:
            Object key in standardized format

        Raises:
            ValueError: If file_type is invalid or required parameters are missing
        """
        if file_type not in ("downloaded", "decrypted"):
            raise ValueError(
                f"Invalid file_type: {file_type}. Must be 'downloaded' or 'decrypted'"
            )

        if file_type == "downloaded":
            if not asin:
                raise ValueError("asin is required for file_type='downloaded'")
            object_key = f"downloaded/{asin}.aax"
            logger.debug(f"Generated object key for downloaded file: {object_key}")
            return object_key

        # file_type == "decrypted"
        if not title:
            raise ValueError("title is required for file_type='decrypted'")

        normalized_title = normalize_filename(title)
        object_key = f"decrypted/{normalized_title}.m4b"
        logger.debug(
            f"Generated object key for decrypted file: {object_key} "
            f"(original title: {title})"
        )
        return object_key

    def _get_user_bucket(self, user_id: str) -> str:
        """Get bucket name for user.

        Implements per-user bucket isolation pattern: user-{user_id}

        Args:
            user_id: User ID

        Returns:
            Bucket name in format: user-{user_id}
        """
        return f"user-{user_id}"

    def ensure_user_bucket(self, user_id: str) -> bool:
        """Ensure user bucket exists, create if not.

        Checks if bucket exists and creates it if necessary.

        Args:
            user_id: User ID for bucket routing

        Returns:
            True if bucket exists or was created successfully, False on error
        """
        bucket_name = self._get_user_bucket(user_id)

        # Check if bucket exists
        if self.minio_client.bucket_exists(bucket_name):
            logger.debug(f"Bucket already exists: {bucket_name}")
            return True

        # Create bucket
        success = self.minio_client.create_bucket(bucket_name)
        if success:
            logger.info(f"Created user bucket: {bucket_name} for user_id={user_id}")
        else:
            logger.error(f"Failed to create bucket: {bucket_name} for user_id={user_id}")

        return success

    def save_file(
        self,
        user_id: str,
        file_path: str,
        file_type: str,
        asin: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Save file to MinIO and return object key.

        1. Generate object key based on file_type
        2. Ensure user bucket exists
        3. Upload file to MinIO
        4. Return (success, object_key)

        Args:
            user_id: User ID for bucket routing
            file_path: Local file path to upload
            file_type: "downloaded" or "decrypted"
            asin: ASIN for downloaded files
            title: Book title for decrypted files

        Returns:
            Tuple of (success: bool, object_key: str or None)
            - success: True if upload succeeded
            - object_key: Generated object key if upload succeeded, None otherwise
        """

        # Generate object key
        try:
            object_key = self._generate_object_key(
                file_type=file_type, asin=asin, title=title
            )
        except ValueError as e:
            logger.error(f"Failed to generate object key: {e}")
            return (False, None)

        # Ensure user bucket exists
        bucket_name = self._get_user_bucket(user_id)
        if not self.ensure_user_bucket(user_id):
            logger.error(f"Failed to ensure bucket exists: {bucket_name}")
            return (False, None)

        # Upload to MinIO
        logger.info(
            f"Uploading file to MinIO: user_id={user_id}, "
            f"file_path={file_path}, object_key={object_key}"
        )

        success = self.minio_client.upload_file(file_path, bucket_name, object_key)

        if success:
            logger.info(
                f"Successfully uploaded to MinIO: user_id={user_id}, "
                f"object_key={object_key}"
            )
            return (True, object_key)
        else:
            logger.error(
                f"Failed to upload to MinIO: user_id={user_id}, "
                f"object_key={object_key}"
            )
            return (False, None)

    def get_file(
        self,
        user_id: str,
        object_key: str,
    ) -> Optional[str]:
        """Download file from MinIO to temp location.

        Downloads the object from MinIO to a temporary file.

        Args:
            user_id: User ID for bucket routing
            object_key: MinIO object key to download

        Returns:
            Temp file path if download succeeds, None on error
        """
        bucket_name = self._get_user_bucket(user_id)

        try:
            # Create temp file for MinIO download
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(object_key).suffix)
            temp_path = temp_file.name
            temp_file.close()

            logger.info(
                f"Downloading from MinIO: user_id={user_id}, "
                f"object_key={object_key} -> {temp_path}"
            )

            success = self.minio_client.download_file(bucket_name, object_key, temp_path)

            if success:
                logger.info(
                    f"Successfully downloaded from MinIO: user_id={user_id}, "
                    f"object_key={object_key}"
                )
                return temp_path
            else:
                # Download failed, clean up temp file
                logger.error(
                    f"MinIO download failed: user_id={user_id}, object_key={object_key}"
                )
                Path(temp_path).unlink(missing_ok=True)
                return None

        except Exception as e:
            logger.error(
                f"Error downloading from MinIO: user_id={user_id}, "
                f"object_key={object_key}, error={e}"
            )
            return None

    def stream_file(
        self,
        user_id: str,
        object_key: str,
        offset: int = 0,
        length: Optional[int] = None,
    ) -> bytes:
        """Stream file from MinIO with Range support.

        Supports HTTP Range requests for audio seeking.

        Args:
            user_id: User ID for bucket routing
            object_key: MinIO object key to stream
            offset: Byte offset to start reading from (for Range requests)
            length: Number of bytes to read (None for all remaining)

        Returns:
            File chunk as bytes, empty bytes on error
        """
        bucket_name = self._get_user_bucket(user_id)

        logger.debug(
            f"Streaming from MinIO: user_id={user_id}, object_key={object_key}, "
            f"offset={offset}, length={length}"
        )

        data = self.minio_client.stream_file(bucket_name, object_key, offset, length)

        if data:
            logger.debug(
                f"Successfully streamed {len(data)} bytes from MinIO: "
                f"user_id={user_id}, object_key={object_key}"
            )
            return data
        else:
            logger.error(
                f"MinIO streaming failed: user_id={user_id}, object_key={object_key}"
            )
            return b""

    def delete_file(self, user_id: str, object_key: str) -> bool:
        """Delete file from MinIO.

        Args:
            user_id: User ID for bucket routing
            object_key: MinIO object key to delete

        Returns:
            True if deletion succeeded, False on error
        """
        bucket_name = self._get_user_bucket(user_id)

        logger.info(
            f"Deleting file from MinIO: user_id={user_id}, object_key={object_key}"
        )

        success = self.minio_client.delete_file(bucket_name, object_key)

        if success:
            logger.info(
                f"Successfully deleted from MinIO: user_id={user_id}, "
                f"object_key={object_key}"
            )
        else:
            logger.error(
                f"Failed to delete from MinIO: user_id={user_id}, "
                f"object_key={object_key}"
            )

        return success
