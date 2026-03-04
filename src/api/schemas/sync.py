"""Sync-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import PaginatedResponse


class SyncCreate(BaseModel):
    """Request model for creating a sync."""

    sync_type: str = Field(
        default="full",
        description="Type of sync (full, incremental, manual)",
        pattern="^(full|incremental|manual)$",
    )


class SyncResponse(BaseModel):
    """Response model for sync information."""

    sync_id: str = Field(
        ...,
        description="Unique sync identifier",
    )
    user_id: str = Field(
        ...,
        description="User ID who initiated this sync",
    )
    sync_type: str = Field(
        ...,
        description="Type of sync (full, incremental, manual)",
    )
    status: str = Field(
        ...,
        description="Sync status (in_progress, completed, partial, failed)",
    )
    sync_started_at: datetime = Field(
        ...,
        description="When the sync started",
    )
    sync_completed_at: Optional[datetime] = Field(
        default=None,
        description="When the sync completed (if finished)",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total duration in seconds (if completed)",
    )
    books_found: int = Field(
        default=0,
        ge=0,
        description="Number of books found in library",
    )
    books_added: int = Field(
        default=0,
        ge=0,
        description="Number of books added to database",
    )
    books_downloaded: int = Field(
        default=0,
        ge=0,
        description="Number of books downloaded",
    )
    books_decrypted: int = Field(
        default=0,
        ge=0,
        description="Number of books decrypted",
    )
    errors_count: int = Field(
        default=0,
        ge=0,
        description="Number of errors encountered",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the sync",
    )
    created_at: datetime = Field(
        ...,
        description="When this record was created",
    )
    updated_at: datetime = Field(
        ...,
        description="When this record was last updated",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "sync_id": "sync-uuid-123",
                "user_id": "user-uuid-456",
                "sync_type": "full",
                "status": "completed",
                "sync_started_at": "2025-12-20T20:00:00Z",
                "sync_completed_at": "2025-12-20T20:15:30Z",
                "duration_seconds": 930.0,
                "books_found": 125,
                "books_added": 3,
                "books_downloaded": 2,
                "books_decrypted": 2,
                "errors_count": 0,
                "notes": "Sync completed successfully",
                "created_at": "2025-12-20T20:00:00Z",
                "updated_at": "2025-12-20T20:15:30Z",
            }
        },
    )


SyncHistoryList = PaginatedResponse[SyncResponse]
"""Type alias for paginated sync history list response."""


class SyncAcceptedResponse(BaseModel):
    """Response for sync trigger (202 Accepted)."""

    sync_id: str = Field(
        ...,
        description="Unique sync identifier",
    )
    status: str = Field(
        default="in_progress",
        description="Initial sync status",
    )
    message: str = Field(
        ...,
        description="Confirmation message",
    )
    sync_started_at: datetime = Field(
        ...,
        description="When the sync started",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sync_id": "sync-uuid-123",
                "status": "in_progress",
                "message": "Sync initiated successfully, running in background",
                "sync_started_at": "2025-12-20T20:00:00Z",
            }
        }
    )
