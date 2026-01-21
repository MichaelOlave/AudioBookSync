"""Book-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import PaginatedResponse


class BookBase(BaseModel):
    """Base book information."""

    asin: str = Field(
        ...,
        description="Amazon Standard Identification Number",
        min_length=10,
        max_length=10,
    )
    title: str = Field(
        ...,
        description="Book title",
        min_length=1,
        max_length=500,
    )
    author: Optional[str] = Field(
        default=None,
        description="Author name",
        max_length=255,
    )
    narrator: Optional[str] = Field(
        default=None,
        description="Narrator name",
        max_length=255,
    )
    series_name: Optional[str] = Field(
        default=None,
        description="Series name if applicable",
        max_length=255,
    )
    description: Optional[str] = Field(
        default=None,
        description="Book description/synopsis",
    )
    rating: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Rating (0.0-5.0)",
    )
    runtime_min: Optional[int] = Field(
        default=None,
        ge=0,
        description="Runtime in minutes",
    )


class BookResponse(BookBase):
    """Book response with metadata."""

    user_id: str = Field(
        ...,
        description="User UUID who owns this book",
    )
    purchase_date: Optional[str] = Field(
        default=None,
        description="Purchase date (YYYY-MM-DD format)",
    )
    is_downloaded: bool = Field(
        default=False,
        description="Whether the book is downloaded",
    )
    is_decrypted: bool = Field(
        default=False,
        description="Whether the book is decrypted",
    )
    download_path: Optional[str] = Field(
        default=None,
        description="Path to downloaded file (if applicable)",
    )
    decrypted_path: Optional[str] = Field(
        default=None,
        description="Path to decrypted file (if applicable)",
    )
    created_at: datetime = Field(
        ...,
        description="When the book was added to library",
    )
    updated_at: datetime = Field(
        ...,
        description="When the book record was last updated",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "asin": "B084L6Z6M3",
                "title": "Becoming",
                "author": "Michelle Obama",
                "narrator": "Michelle Obama",
                "series_name": None,
                "description": "An intimate, powerful, and inspiring memoir...",
                "rating": 4.8,
                "runtime_min": 1440,
                "user_id": "user-uuid-123",
                "purchase_date": "2023-01-15",
                "is_downloaded": True,
                "is_decrypted": True,
                "download_path": "/audiobooks/downloaded/B084L6Z6M3.m4b",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": "2023-01-15T10:30:00Z",
                "updated_at": "2023-01-15T10:30:00Z",
            }
        },
    )


BookList = PaginatedResponse[BookResponse]
"""Type alias for paginated book list response."""
