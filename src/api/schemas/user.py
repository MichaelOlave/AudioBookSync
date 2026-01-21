"""Pydantic schemas for user endpoints."""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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

    model_config = ConfigDict(from_attributes=True)


class UserWithAuth(UserResponse):
    """Schema for user with authentication details (admin view)."""

    auth_file_path: Optional[str] = Field(
        default=None,
        description="Path to Audible auth file",
    )
    activation_bytes: Optional[str] = Field(
        default=None,
        description="DRM activation bytes (redacted)",
    )


class PasswordChangeRequest(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(
        ...,
        min_length=1,
        description="Current password for verification",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password (must contain uppercase, lowercase, digit, special char)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            raise ValueError("Password must contain special character")
        return v


class EmailChangeRequest(BaseModel):
    """Schema for email change request."""

    password: str = Field(
        ...,
        min_length=1,
        description="Current password for verification",
    )
    new_email: EmailStr = Field(
        ...,
        description="New email address",
    )


class EmailChangeResponse(BaseModel):
    """Schema for email change response."""

    message: str = Field(
        ...,
        description="Success message",
    )
    success: bool = Field(
        default=True,
        description="Whether operation was successful",
    )
    email: str = Field(
        ...,
        description="New email address",
    )
