"""Schemas for task monitoring endpoints."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskType(str, Enum):
    """Task operation types."""

    DOWNLOAD = "download"
    DECRYPTION = "decryption"
    SYNC = "sync"


class ActiveTaskResponse(BaseModel):
    """Unified response for an active task."""

    task_id: str = Field(description="Task UUID")
    task_type: TaskType = Field(description="Type of operation")
    status: str = Field(description="Current status")

    # Book/Content Info (for downloads/decryptions)
    asin: Optional[str] = Field(None, description="Book ASIN")
    title: Optional[str] = Field(None, description="Book title")

    # Progress Info
    progress_percentage: Optional[int] = Field(
        None, ge=0, le=100, description="Progress (0-100)"
    )
    started_at: datetime = Field(description="When task started")

    # Download/Decryption specific
    attempt_number: Optional[int] = Field(None, description="Attempt number")

    # Sync specific
    sync_type: Optional[str] = Field(None, description="Sync type (full/partial)")
    books_found: Optional[int] = Field(None, description="Total books found")
    books_added: Optional[int] = Field(None, description="Books added so far")

    # Error tracking
    error_message: Optional[str] = Field(None, description="Latest error if any")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_type": "download",
                "status": "downloading",
                "asin": "B084L6Z6M3",
                "title": "Example Book",
                "progress_percentage": None,
                "started_at": "2024-01-22T10:30:00Z",
                "attempt_number": 1,
                "error_message": None,
            }
        }
    )


class ActiveTasksList(BaseModel):
    """Response containing all active tasks grouped by type."""

    downloads: List[ActiveTaskResponse] = Field(default_factory=list)
    decryptions: List[ActiveTaskResponse] = Field(default_factory=list)
    syncs: List[ActiveTaskResponse] = Field(default_factory=list)
    total_active: int = Field(description="Total number of active tasks")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "downloads": [],
                "decryptions": [],
                "syncs": [],
                "total_active": 0,
                "timestamp": "2024-01-22T10:35:00Z",
            }
        }
    )


class TaskCancelResponse(BaseModel):
    """Response for task cancellation."""

    task_id: str
    task_type: TaskType
    status: str
    message: str
    success: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_type": "download",
                "status": "cancelled",
                "message": "Task cancelled successfully",
                "success": True,
            }
        }
    )
