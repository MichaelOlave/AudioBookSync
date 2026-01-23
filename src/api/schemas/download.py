"""Schemas for download-related API requests and responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .common import BookActionCreate, PaginatedResponse

class DownloadCreate(BookActionCreate):
    """Request to initiate a book download."""

class DownloadResponse(BaseModel):
    """Download status response."""

    download_id: UUID = Field(
        ...,
        description="Unique download identifier (UUID)",
    )
    asin: str = Field(
        ...,
        description="Book ASIN",
    )
    status: str = Field(
        ...,
        description="Download status: pending, downloading, completed, failed, cancelled",
    )
    download_path: Optional[str] = Field(
        default=None,
        description="Path to downloaded file",
    )
    file_size_bytes: Optional[int] = Field(
        default=None,
        description="Downloaded file size in bytes",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if download failed",
    )
    download_started_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when download started",
    )
    download_completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when download completed",
    )
    message: Optional[str] = Field(
        default=None,
        description="Status message",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "download_id": "550e8400-e29b-41d4-a716-446655440000",
                "asin": "B084L6Z6M3",
                "status": "downloading",
                "message": "Download initiated",
                "download_started_at": "2024-12-22T10:30:00",
            }
        }
    )

DownloadList = PaginatedResponse[DownloadResponse]
"""Type alias for paginated download list response."""
