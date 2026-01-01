"""Common/shared Pydantic schemas for API responses."""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")  # Generic type for pagination


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (starting from 1)",
    )
    page_size: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of items per page (1-100)",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T] = Field(
        ...,
        description="List of items for this page",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items across all pages",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Number of items per page",
    )
    pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 50,
                "pages": 0,
            }
        }
    )


class MessageResponse(BaseModel):
    """Simple message response for operations like delete."""

    message: str = Field(
        ...,
        description="Success or status message",
    )
    success: bool = Field(
        default=True,
        description="Whether operation was successful",
    )


class ErrorResponse(BaseModel):
    """Standard error response structure."""

    error: str = Field(
        ...,
        description="Error type/name",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    status_code: int = Field(
        ...,
        description="HTTP status code",
    )
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details (if applicable)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "ValidationError",
                "message": "Request validation failed",
                "status_code": 422,
                "details": {"field_name": "error message"},
            }
        }
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(
        default="healthy",
        description="Service health status",
    )
    service: str = Field(
        default="AudioBookSync",
        description="Service name",
    )
    version: Optional[str] = Field(
        default=None,
        description="API version",
    )
    minio: Optional[str] = Field(
        default=None,
        description="MinIO storage connectivity status: 'connected', 'disconnected', or error message",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "service": "AudioBookSync",
                "version": "1.0.0",
                "minio": "connected",
            }
        }
    )
