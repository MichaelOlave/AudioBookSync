"""AWS S3 file storage adapter for hexagonal architecture.

This module implements the FileStoragePort interface using AWS S3 as the storage backend.

Following hexagonal architecture principles:
- Port: FileStoragePort (interface defining storage operations)
- Adapter: S3StorageAdapter (this module - implements port for AWS S3)
"""

import tempfile
from pathlib import Path
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from src.infrastructure.file_utils import normalize_filename
from src.ports.file_storage_port import FileStoragePort


class S3StorageAdapter(FileStoragePort):
    """AWS S3 adapter implementing FileStoragePort.

    Provides file storage operations using AWS S3 as the backend with per-user
    bucket isolation. This is a concrete implementation of the FileStoragePort interface.

    Features:
    - Per-user bucket isolation: user-{user_id} bucket pattern
    - HTTP Range request support for audio streaming (via S3 object metadata)
    - Direct S3 access with boto3
    - Comprehensive error handling and logging

    Configuration:
        Requires AWS credentials to be configured via:
        - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables
        - AWS credentials file (~/.aws/credentials)
        - IAM role (when running on AWS infrastructure)

        Required S3 permissions:
        - s3:CreateBucket
        - s3:ListBucket
        - s3:GetObject
        - s3:PutObject
        - s3:DeleteObject

    Example usage:
        storage = S3StorageAdapter(region_name="us-east-1")

        # Save file (uploads to S3)
        success, object_key = storage.save_file(
            user_id="user-123",
            file_path="/path/to/book.aax",
            file_type="downloaded",
            asin="B001ABC123"
        )

        # Stream file with Range support
        chunk = storage.stream_file(
            user_id="user-123",
            object_key="decrypted/audiobook.m4b",
            offset=1024,
            length=8192
        )
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        s3_client=None,
        bucket_name: Optional[str] = None,
    ):
        """Initialize S3StorageAdapter with boto3 S3 client.

        Args:
            region_name: AWS region for S3 operations (default: us-east-1)
            s3_client: Boto3 S3 client for testing (dependency injection).
                      If None, creates new client with given region.
            bucket_name: Optional custom bucket name. If provided, all files are stored
                        in this bucket. If None, uses per-user bucket pattern (user-{user_id}).
        """
        self.region_name = region_name
        self.s3_client = s3_client if s3_client else boto3.client("s3", region_name=region_name)
        self.bucket_name = bucket_name
        logger.info(f"S3StorageAdapter initialized with region: {region_name}, bucket_name: {bucket_name}")

    def _generate_object_key(
        self, file_type: str, asin: Optional[str] = None, title: Optional[str] = None
    ) -> str:
        """Generate S3 object key for file storage.

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
            raise ValueError(f"Invalid file_type: {file_type}. Must be 'downloaded' or 'decrypted'")

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
        """Get S3 bucket name for user.

        If a custom bucket_name was configured, returns it.
        Otherwise, implements per-user bucket isolation pattern: user-{user_id}

        Args:
            user_id: User ID

        Returns:
            Bucket name: either configured bucket_name or user-{user_id} pattern
        """
        if self.bucket_name:
            return self.bucket_name
        return f"user-{user_id}"

    def ensure_user_bucket(self, user_id: str) -> bool:
        """Ensure S3 bucket exists for user, create if not.

        Checks if bucket exists and creates it if necessary.

        Args:
            user_id: User ID for bucket routing

        Returns:
            True if bucket exists or was created successfully, False on error
        """
        bucket_name = self._get_user_bucket(user_id)

        try:
            # Check if bucket exists by trying to get its location
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.debug(f"Bucket already exists: {bucket_name}")
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                # Bucket doesn't exist, create it
                try:
                    if self.region_name == "us-east-1":
                        # us-east-1 doesn't accept LocationConstraint
                        self.s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": self.region_name},
                        )
                    logger.info(f"Created user bucket: {bucket_name} for user_id={user_id}")
                    return True
                except ClientError as create_error:
                    logger.error(
                        f"Failed to create bucket: {bucket_name} for user_id={user_id}, "
                        f"error={create_error}"
                    )
                    return False
            else:
                logger.error(
                    f"Error checking bucket {bucket_name} for user_id={user_id}, "
                    f"error_code={error_code}"
                )
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking bucket {bucket_name}: {e}")
            return False

    def save_file(
        self,
        user_id: str,
        file_path: str,
        file_type: str,
        asin: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Save file to S3 and return object key.

        1. Generate object key based on file_type
        2. Ensure user bucket exists
        3. Upload file to S3
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
            object_key = self._generate_object_key(file_type=file_type, asin=asin, title=title)
        except ValueError as e:
            logger.error(f"Failed to generate object key: {e}")
            return (False, None)

        # Ensure user bucket exists
        bucket_name = self._get_user_bucket(user_id)
        if not self.ensure_user_bucket(user_id):
            logger.error(f"Failed to ensure bucket exists: {bucket_name}")
            return (False, None)

        # Upload to S3
        logger.info(
            f"Uploading file to S3: user_id={user_id}, "
            f"file_path={file_path}, object_key={object_key}"
        )

        try:
            self.s3_client.upload_file(file_path, bucket_name, object_key)
            logger.info(
                f"Successfully uploaded to S3: user_id={user_id}, "
                f"object_key={object_key}"
            )
            return (True, object_key)
        except ClientError as e:
            logger.error(
                f"Failed to upload to S3: user_id={user_id}, "
                f"object_key={object_key}, error={e}"
            )
            return (False, None)
        except Exception as e:
            logger.error(
                f"Unexpected error uploading to S3: user_id={user_id}, "
                f"object_key={object_key}, error={e}"
            )
            return (False, None)

    def get_file(
        self,
        user_id: str,
        object_key: str,
    ) -> Optional[str]:
        """Download file from S3 to temp location.

        Downloads the object from S3 to a temporary file.

        Args:
            user_id: User ID for bucket routing
            object_key: S3 object key to download

        Returns:
            Temp file path if download succeeds, None on error
        """
        bucket_name = self._get_user_bucket(user_id)
        temp_path = None

        try:
            # Create temp file for S3 download
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(object_key).suffix)
            temp_path = temp_file.name
            temp_file.close()

            logger.info(
                f"Downloading from S3: user_id={user_id}, "
                f"object_key={object_key} -> {temp_path}"
            )

            self.s3_client.download_file(bucket_name, object_key, temp_path)

            logger.info(
                f"Successfully downloaded from S3: user_id={user_id}, "
                f"object_key={object_key}"
            )
            return temp_path

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                logger.warning(f"S3 object not found: user_id={user_id}, object_key={object_key}")
            else:
                logger.error(
                    f"S3 download failed: user_id={user_id}, object_key={object_key}, "
                    f"error={e}"
                )
            # Clean up temp file on failure
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
            return None
        except Exception as e:
            logger.error(
                f"Error downloading from S3: user_id={user_id}, "
                f"object_key={object_key}, error={e}"
            )
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
            return None

    def stream_file(
        self,
        user_id: str,
        object_key: str,
        offset: int = 0,
        length: Optional[int] = None,
    ) -> bytes:
        """Stream file from S3 with Range support.

        Supports HTTP Range requests for audio seeking.

        Args:
            user_id: User ID for bucket routing
            object_key: S3 object key to stream
            offset: Byte offset to start reading from
            length: Number of bytes to read (None for remaining)

        Returns:
            File chunk as bytes, empty bytes on error
        """
        bucket_name = self._get_user_bucket(user_id)

        logger.debug(
            f"Streaming from S3: user_id={user_id}, object_key={object_key}, "
            f"offset={offset}, length={length}"
        )

        try:
            # Build Range header for S3 get_object
            range_header = None
            if length is not None:
                end = offset + length - 1
                range_header = f"bytes={offset}-{end}"
            elif offset > 0:
                range_header = f"bytes={offset}-"

            # Get object from S3
            if range_header:
                response = self.s3_client.get_object(
                    Bucket=bucket_name, Key=object_key, Range=range_header
                )
            else:
                response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)

            # Read file content
            data = response["Body"].read()

            logger.debug(
                f"Successfully streamed {len(data)} bytes from S3: "
                f"user_id={user_id}, object_key={object_key}"
            )
            return data

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                logger.warning(f"S3 object not found: user_id={user_id}, object_key={object_key}")
            else:
                logger.error(
                    f"S3 streaming failed: user_id={user_id}, object_key={object_key}, "
                    f"error={e}"
                )
            return b""
        except Exception as e:
            logger.error(
                f"Error streaming from S3: user_id={user_id}, "
                f"object_key={object_key}, error={e}"
            )
            return b""

    def delete_file(self, user_id: str, object_key: str) -> bool:
        """Delete file from S3.

        Args:
            user_id: User ID for bucket routing
            object_key: S3 object key to delete

        Returns:
            True if deletion succeeded, False on error
        """
        bucket_name = self._get_user_bucket(user_id)

        logger.info(f"Deleting file from S3: user_id={user_id}, object_key={object_key}")

        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=object_key)
            logger.info(
                f"Successfully deleted from S3: user_id={user_id}, "
                f"object_key={object_key}"
            )
            return True
        except ClientError as e:
            logger.error(
                f"Failed to delete from S3: user_id={user_id}, "
                f"object_key={object_key}, error={e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error deleting from S3: user_id={user_id}, "
                f"object_key={object_key}, error={e}"
            )
            return False

    def file_exists(self, user_id: str, object_key: str) -> bool:
        """Check if file exists in S3.

        Args:
            user_id: User ID for bucket routing
            object_key: S3 object key to check

        Returns:
            True if file exists, False otherwise
        """
        bucket_name = self._get_user_bucket(user_id)

        logger.debug(f"Checking if file exists in S3: user_id={user_id}, object_key={object_key}")

        try:
            self.s3_client.head_object(Bucket=bucket_name, Key=object_key)
            logger.debug(f"File exists in S3: user_id={user_id}, object_key={object_key}")
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                logger.debug(f"File does not exist in S3: user_id={user_id}, object_key={object_key}")
            else:
                logger.debug(
                    f"Error checking file in S3: user_id={user_id}, "
                    f"object_key={object_key}, error_code={error_code}"
                )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error checking file in S3: user_id={user_id}, "
                f"object_key={object_key}, error={e}"
            )
            return False
