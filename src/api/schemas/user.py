"""Pydantic schemas for user endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username",
    )
    email: EmailStr = Field(
        ...,
        description="Email address",
    )


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(
        ...,
        min_length=8,
        description="Password (minimum 8 characters)",
    )


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: Optional[EmailStr] = Field(
        default=None,
        description="New email address",
    )
    auth_file_path: Optional[str] = Field(
        default=None,
        description="Path to Audible auth file",
    )
    activation_bytes: Optional[str] = Field(
        default=None,
        description="DRM activation bytes",
    )


class UserResponse(UserBase):
    """Schema for user response (no sensitive data)."""

    user_id: UUID = Field(
        ...,
        description="Unique user identifier",
    )
    is_active: bool = Field(
        default=True,
        description="Whether user account is active",
    )
    last_sync_date: Optional[datetime] = Field(
        default=None,
        description="Date of last library sync",
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )

    model_config = ConfigDict(
        from_attributes=True
    )


class UserWithAuth(UserResponse):
    """Schema for user with authentication details (admin view)."""

    auth_file_path: Optional[str] = Field(
        default=None,
        description="Path to Audible auth file",
    )
    activation_bytes: Optional[str] = Field(
        default=None,
        description="DRM activation bytes (redacted)",
    ), ConfigDict