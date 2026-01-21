"""WebSocket event types and structures for real-time updates."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """WebSocket event types."""

    # Sync events
    SYNC_STARTED = "sync.started"
    SYNC_PROGRESS = "sync.progress"
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"

    # Download events
    DOWNLOAD_STARTED = "download.started"
    DOWNLOAD_PROGRESS = "download.progress"
    DOWNLOAD_COMPLETED = "download.completed"
    DOWNLOAD_FAILED = "download.failed"

    # Decryption events
    DECRYPT_STARTED = "decrypt.started"
    DECRYPT_PROGRESS = "decrypt.progress"
    DECRYPT_COMPLETED = "decrypt.completed"
    DECRYPT_FAILED = "decrypt.failed"

    # System events
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    MESSAGE = "message"


class SyncStartedEvent(BaseModel):
    """Sync started event data."""

    sync_id: str = Field(
        ...,
        description="Unique sync identifier",
    )
    sync_type: str = Field(
        ...,
        description="Type of sync (full, incremental, manual)",
    )
    timestamp: float = Field(
        ...,
        description="Event timestamp (Unix timestamp)",
    )


class SyncProgressEvent(BaseModel):
    """Sync progress event data."""

    sync_id: str = Field(
        ...,
        description="Unique sync identifier",
    )
    current_book: Optional[str] = Field(
        default=None,
        description="Current book being processed (ASIN)",
    )
    books_processed: int = Field(
        default=0,
        description="Number of books processed so far",
    )
    books_total: int = Field(
        default=0,
        description="Total number of books to process",
    )
    progress_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall progress percentage",
    )
    status: str = Field(
        default="in_progress",
        description="Current status of the operation",
    )
    timestamp: float = Field(
        ...,
        description="Event timestamp (Unix timestamp)",
    )


class SyncCompletedEvent(BaseModel):
    """Sync completed event data."""

    sync_id: str = Field(
        ...,
        description="Unique sync identifier",
    )
    status: str = Field(
        ...,
        description="Final sync status (completed, partial, failed)",
    )
    books_found: int = Field(
        default=0,
        description="Number of books found",
    )
    books_added: int = Field(
        default=0,
        description="Number of books added to library",
    )
    books_downloaded: int = Field(
        default=0,
        description="Number of books downloaded",
    )
    books_decrypted: int = Field(
        default=0,
        description="Number of books decrypted",
    )
    errors_count: int = Field(
        default=0,
        description="Number of errors encountered",
    )
    duration_seconds: float = Field(
        default=0.0,
        description="Total duration in seconds",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the sync",
    )
    timestamp: float = Field(
        ...,
        description="Event timestamp (Unix timestamp)",
    )


class SyncFailedEvent(BaseModel):
    """Sync failed event data."""

    sync_id: str = Field(
        ...,
        description="Unique sync identifier",
    )
    error: str = Field(
        ...,
        description="Error message",
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Error code for categorization",
    )
    timestamp: float = Field(
        ...,
        description="Event timestamp (Unix timestamp)",
    )


class DownloadProgressEvent(BaseModel):
    """Download progress event data."""

    asin: str = Field(
        ...,
        description="Book ASIN",
    )
    filename: str = Field(
        ...,
        description="Download filename",
    )
    bytes_downloaded: int = Field(
        default=0,
        description="Bytes downloaded so far",
    )
    total_bytes: int = Field(
        default=0,
        description="Total bytes to download",
    )
    progress_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Download progress percentage",
    )
    speed_kbps: float = Field(
        default=0.0,
        description="Download speed in KB/s",
    )
    timestamp: float = Field(
        ...,
        description="Event timestamp (Unix timestamp)",
    )


class ErrorEvent(BaseModel):
    """Error event data."""

    code: str = Field(
        ...,
        description="Error code",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details",
    )
    timestamp: float = Field(
        ...,
        description="Event timestamp (Unix timestamp)",
    )
