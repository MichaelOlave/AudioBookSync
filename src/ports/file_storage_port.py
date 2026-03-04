"""File storage port (interface) for hexagonal architecture.

This module defines the contract for file storage implementations.
Implementations can provide storage via MinIO, AWS S3, GCS, local filesystem, etc.

Following hexagonal architecture principles:
- Port: defines what file storage operations are needed (this module)
- Adapter: implements the port for a specific storage backend
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class FileStoragePort(ABC):
    """Abstract port defining file storage operations.

    This port defines the contract that any file storage implementation must follow.
    It abstracts away the details of where files are actually stored.

    Example usage:
        storage: FileStoragePort = MinIOStorageAdapter()

        # Save file
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

    @abstractmethod
    def ensure_user_bucket(self, user_id: str) -> bool:
        """Ensure storage space exists for user.

        Creates storage bucket/directory if it doesn't exist.
        Implementation detail is abstracted away.

        Args:
            user_id: User ID for storage isolation

        Returns:
            True if storage space exists or was created, False on error
        """

    @abstractmethod
    def save_file(
        self,
        user_id: str,
        file_path: str,
        file_type: str,
        asin: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Save file to storage and return storage key.

        Args:
            user_id: User ID for storage isolation
            file_path: Local file path to upload
            file_type: "downloaded" or "decrypted"
            asin: ASIN for downloaded files
            title: Book title for decrypted files

        Returns:
            Tuple of (success: bool, storage_key: str or None)
            - success: True if save succeeded
            - storage_key: Generated storage key if successful, None otherwise
        """

    @abstractmethod
    def get_file(self, user_id: str, object_key: str) -> Optional[str]:
        """Retrieve file from storage to a local temp location.

        Args:
            user_id: User ID for storage isolation
            object_key: Storage key of file to retrieve

        Returns:
            Temp file path if successful, None on error
        """

    @abstractmethod
    def stream_file(
        self,
        user_id: str,
        object_key: str,
        offset: int = 0,
        length: Optional[int] = None,
    ) -> bytes:
        """Stream file chunk from storage with Range support.

        Useful for audio seeking via HTTP Range requests.

        Args:
            user_id: User ID for storage isolation
            object_key: Storage key of file to stream
            offset: Byte offset to start reading from
            length: Number of bytes to read (None for remaining)

        Returns:
            File chunk as bytes, empty bytes on error
        """

    @abstractmethod
    def delete_file(self, user_id: str, object_key: str) -> bool:
        """Delete file from storage.

        Args:
            user_id: User ID for storage isolation
            object_key: Storage key of file to delete

        Returns:
            True if deletion succeeded, False on error
        """

    @abstractmethod
    def file_exists(self, user_id: str, object_key: str) -> bool:
        """Check if file exists in storage.

        Args:
            user_id: User ID for storage isolation
            object_key: Storage key of file to check

        Returns:
            True if file exists, False otherwise
        """
