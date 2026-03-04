"""Book-related Pydantic schemas."""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

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

    user_id: UUID = Field(
        ...,
        description="User UUID who owns this book",
    )
    purchase_date: Optional[date] = Field(
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
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
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


class BookMetadataResponse(BaseModel):
    """Flexible book metadata response."""

    metadata_id: UUID = Field(
        ...,
        description="Metadata UUID",
    )
    asin: str = Field(
        ...,
        description="Amazon Standard Identification Number",
    )
    title: Optional[str] = Field(default=None, description="Book title")
    subtitle: Optional[str] = Field(default=None, description="Book subtitle")
    language: Optional[str] = Field(default=None, description="Language code")
    publisher_name: Optional[str] = Field(default=None, description="Publisher name")
    format_type: Optional[str] = Field(default=None, description="Format type")
    content_type: Optional[str] = Field(default=None, description="Content type")
    content_delivery_type: Optional[str] = Field(default=None, description="Content delivery type")
    status: Optional[str] = Field(default=None, description="Content status")
    publication_datetime: Optional[datetime] = Field(
        default=None,
        description="Publication datetime",
    )
    release_date: Optional[datetime] = Field(default=None, description="Release date")
    issue_date: Optional[datetime] = Field(default=None, description="Issue date")
    purchase_date: Optional[datetime] = Field(default=None, description="Purchase date")
    runtime_length_min: Optional[int] = Field(default=None, description="Runtime in minutes")
    is_listenable: Optional[bool] = Field(default=None, description="Listenability flag")
    is_purchasability_suppressed: Optional[bool] = Field(
        default=None,
        description="Purchasability suppressed flag",
    )
    is_adult_product: Optional[bool] = Field(default=None, description="Adult content flag")
    has_children: Optional[bool] = Field(default=None, description="Has children flag")
    origin_asin: Optional[str] = Field(default=None, description="Origin ASIN")
    sku: Optional[str] = Field(default=None, description="SKU")
    isbn: Optional[str] = Field(default=None, description="ISBN")
    parent_asin: Optional[str] = Field(default=None, description="Parent ASIN")
    brand: Optional[str] = Field(default=None, description="Brand")
    authors: Optional[Any] = Field(default=None, description="Authors list")
    narrators: Optional[Any] = Field(default=None, description="Narrators list")
    rating: Optional[Any] = Field(default=None, description="Rating details")
    product_images: Optional[Any] = Field(default=None, description="Product image URLs")
    social_media_images: Optional[Any] = Field(default=None, description="Social image URLs")
    available_codecs: Optional[Any] = Field(default=None, description="Available codecs")
    library_status: Optional[Any] = Field(default=None, description="Library status")
    thesaurus_subject_keywords: Optional[Any] = Field(default=None, description="Subject keywords")
    periodical_info: Optional[Any] = Field(default=None, description="Periodical info")
    relationships: Optional[Any] = Field(default=None, description="Relationship data")
    badges: Optional[Any] = Field(default=None, description="Badges")
    claim_code_url: Optional[str] = Field(default=None, description="Claim code URL")
    rating_distribution: Optional[Any] = Field(
        default=None,
        description="Rating distribution",
    )
    custom_metadata: Optional[Any] = Field(
        default=None,
        description="Custom metadata",
    )
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    model_config = ConfigDict(from_attributes=True)


class ChapterResponse(BaseModel):
    """Chapter metadata response."""

    chapter_id: UUID = Field(..., description="Chapter UUID")
    asin: str = Field(..., description="Amazon Standard Identification Number")
    sequence_number: int = Field(..., description="Chapter sequence number")
    title: Optional[str] = Field(default=None, description="Chapter title")
    start_offset_ms: Optional[int] = Field(default=None, description="Start offset in ms")
    end_offset_ms: Optional[int] = Field(default=None, description="End offset in ms")
    length_ms: Optional[int] = Field(default=None, description="Chapter length in ms")
    raw_metadata: Optional[Any] = Field(default=None, description="Raw chapter metadata payload")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    model_config = ConfigDict(from_attributes=True)


class BookDashboardBook(BaseModel):
    """Book details for dashboard views."""

    asin: str = Field(
        ...,
        description="Amazon Standard Identification Number",
    )
    user_id: UUID = Field(
        ...,
        description="User UUID who owns this book",
    )
    title: str = Field(
        ...,
        description="Book title",
    )
    subtitle: Optional[str] = Field(default=None, description="Book subtitle")
    author: Optional[str] = Field(default=None, description="Author name")
    narrator: Optional[str] = Field(default=None, description="Narrator name")
    series_name: Optional[str] = Field(default=None, description="Series name")
    series_sequence: Optional[str] = Field(default=None, description="Series sequence")
    publisher: Optional[str] = Field(default=None, description="Publisher name")
    publication_date: Optional[date] = Field(default=None, description="Publication date")
    purchase_date: Optional[date] = Field(default=None, description="Purchase date")
    description: Optional[str] = Field(default=None, description="Book description")
    language: Optional[str] = Field(default=None, description="Language code")
    runtime_min: Optional[int] = Field(default=None, description="Runtime in minutes")
    rating: Optional[float] = Field(default=None, description="Rating (0.0-5.0)")
    review_count: Optional[int] = Field(default=None, description="Review count")
    cover_art_url: Optional[str] = Field(default=None, description="Cover art URL")
    file_size_bytes: Optional[int] = Field(default=None, description="Downloaded file size")
    checksum: Optional[str] = Field(default=None, description="File checksum")
    is_downloaded: bool = Field(default=False, description="Whether the book is downloaded")
    is_decrypted: bool = Field(default=False, description="Whether the book is decrypted")
    download_path: Optional[str] = Field(
        default=None,
        description="Download path",
    )
    decrypted_path: Optional[str] = Field(
        default=None,
        description="Decrypted path",
    )
    created_at: datetime = Field(..., description="When the book was added")
    updated_at: datetime = Field(..., description="When the book was last updated")

    model_config = ConfigDict(from_attributes=True)


class BookDashboardResponse(BaseModel):
    """Dashboard response with book and metadata details."""

    book: BookDashboardBook = Field(..., description="Book details")
    metadata: Optional[BookMetadataResponse] = Field(
        default=None,
        description="Extended metadata",
    )


BookList = PaginatedResponse[BookResponse]
"""Type alias for paginated book list response."""
