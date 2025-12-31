"""Schemas for download-related API requests and responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DownloadCreate(BaseModel):
    """Request to initiate a book download."""

    asin: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="Amazon Standard Identification Number (10 characters)",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Book title",
    )

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "asin": "B084L6Z6M3",
                "title": "Becoming",
            }
        }
    )


class DownloadResponse(BaseModel):
    """Download status response."""

    download_id: str = Field(
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
        json_schema_extra = {
            "example": {
                "download_id": "550e8400-e29b-41d4-a716-446655440000",
                "asin": "B084L6Z6M3",
                "status": "downloading",
                "message": "Download initiated",
                "download_started_at": "2024-12-22T10:30:00",
            }
        }
    )


class DownloadList(BaseModel):
    """Paginated list of downloads."""

    items: list[DownloadResponse] = Field(
        default_factory=list,
        description="List of download records",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of downloads (unfiltered)",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=50,
        description="Number of items per page",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "download_id": "550e8400-e29b-41d4-a716-446655440000",
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                    }
                ],
                "total": 15,
                "page": 1,
                "page_size": 10,
            }
        }
    )