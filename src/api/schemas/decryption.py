"""Schemas for decryption-related API requests and responses."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .common import BookActionCreate, PaginatedResponse


class DecryptCreate(BookActionCreate):
    """Request to initiate book decryption."""


class DecryptResponse(BaseModel):
    """Decryption status response."""

    decryption_id: UUID = Field(
        ...,
        description="Unique decryption identifier (UUID)",
    )
    asin: str = Field(
        ...,
        description="Book ASIN",
    )
    status: str = Field(
        ...,
        description="Decryption status: pending, decrypting, completed, failed, cancelled",
    )
    download_id: Optional[UUID] = Field(
        default=None,
        description="ID of associated download",
    )
    input_path: Optional[str] = Field(
        default=None,
        description="Path to encrypted input file",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Path to decrypted output file",
    )
    output_format: Optional[str] = Field(
        default=None,
        description="Output audio format (e.g., m4b, mp3)",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if decryption failed",
    )
    decryption_started_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when decryption started",
    )
    decryption_completed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when decryption completed",
    )
    message: Optional[str] = Field(
        default=None,
        description="Status message",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "decryption_id": "550e8400-e29b-41d4-a716-446655440000",
                "asin": "B084L6Z6M3",
                "status": "decrypting",
                "output_format": "m4b",
                "message": "Decryption initiated",
                "decryption_started_at": "2024-12-22T10:30:00",
            }
        },
    )


DecryptList = PaginatedResponse[DecryptResponse]
"""Type alias for paginated decryption list response."""
