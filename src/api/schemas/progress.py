"""Schemas for reading progress API requests and responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReadingProgressUpdate(BaseModel):
    """Request to update reading progress for a book."""

    percent_complete: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
        description="Percent of the book completed (0-100)",
    )
    position_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Playback position in milliseconds",
    )
    is_finished: Optional[bool] = Field(
        default=None,
        description="Whether the book is finished",
    )


class ReadingProgressResponse(BaseModel):
    """Reading progress response."""

    progress_id: UUID = Field(
        ...,
        description="Unique reading progress identifier (UUID)",
    )
    asin: str = Field(
        ...,
        description="Book ASIN",
    )
    percent_complete: int = Field(
        ...,
        description="Percent completed (0-100)",
    )
    position_ms: int = Field(
        ...,
        description="Playback position in milliseconds",
    )
    is_finished: bool = Field(
        ...,
        description="Whether the book is finished",
    )
    date_started: Optional[datetime] = Field(
        default=None,
        description="When playback started (if tracked)",
    )
    date_finished: Optional[datetime] = Field(
        default=None,
        description="When playback finished (if completed)",
    )
    last_position_update: Optional[datetime] = Field(
        default=None,
        description="Last time the playback position was updated",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "progress_id": "550e8400-e29b-41d4-a716-446655440000",
                "asin": "B084L6Z6M3",
                "percent_complete": 42,
                "position_ms": 1234567,
                "is_finished": False,
                "date_started": "2024-12-22T10:30:00",
                "date_finished": None,
                "last_position_update": "2024-12-22T11:10:00",
            }
        },
    )
