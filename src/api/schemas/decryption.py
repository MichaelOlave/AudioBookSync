"""Schemas for decryption-related API requests and responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DecryptCreate(BaseModel):
    """Request to initiate book decryption."""

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
        json_schema_extra={
            "example": {
                "asin": "B084L6Z6M3",
                "title": "Becoming",
            }
        }
    )


class DecryptResponse(BaseModel):
    """Decryption status response."""

    decryption_id: str = Field(
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
    download_id: Optional[str] = Field(
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
        json_schema_extra={
            "example": {
                "decryption_id": "550e8400-e29b-41d4-a716-446655440000",
                "asin": "B084L6Z6M3",
                "status": "decrypting",
                "output_format": "m4b",
                "message": "Decryption initiated",
                "decryption_started_at": "2024-12-22T10:30:00",
            }
        }
    )


class DecryptList(BaseModel):
    """Paginated list of decryptions."""

    items: list[DecryptResponse] = Field(
        default_factory=list,
        description="List of decryption records",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of decryptions (unfiltered)",
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
                        "decryption_id": "550e8400-e29b-41d4-a716-446655440000",
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                        "output_format": "m4b",
                    }
                ],
                "total": 8,
                "page": 1,
                "page_size": 10,
            }
        }
    )
