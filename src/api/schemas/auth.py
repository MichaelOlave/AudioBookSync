"""Pydantic schemas for authentication endpoints."""

import re
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Schema for user registration request."""

    username: str = Field(
        default=...,
        min_length=3,
        max_length=50,
        description="Username (3-50 characters)",
        json_schema_extra={"example": "john_doe"},
    )
    email: EmailStr = Field(
        default=...,
        description="User's email address",
        json_schema_extra={"example": "john@example.com"},
    )
    password: str = Field(
        default=...,
        min_length=8,
        max_length=100,
        description="Password (minimum 8 characters, must contain uppercase, lowercase, digit, and special character)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};:,.<>?]", v):
            raise ValueError("Password must contain at least one special character")
        if re.search(r"\s", v):
            raise ValueError("Password cannot contain whitespace")
        return v


class UserLogin(BaseModel):
    """Schema for user login request (OAuth2 compatible)."""

    username: str = Field(
        default=...,
        description="Username or email",
        json_schema_extra={"example": "john_doe"},
    )
    password: str = Field(
        default=...,
        description="User's password",
    )


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(
        description="JWT access token for API requests",
    )
    refresh_token: str = Field(
        description="JWT refresh token for obtaining new access tokens",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
    )


class TokenPayload(BaseModel):
    """Schema for JWT token payload (internal use)."""

    sub: str = Field(
        description="Subject (user_id)",
    )
    exp: int = Field(
        description="Expiration timestamp",
    )
    iat: int = Field(
        description="Issued at timestamp",
    )
    type: str = Field(
        description="Token type ('access' or 'refresh')",
    )
    jti: str = Field(
        description="JWT ID (unique identifier)",
    )


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(
        description="The refresh token to use for obtaining a new access token",
    )


class AuthStartRequest(BaseModel):
    """Request to start Audible authentication."""

    country_code: str = Field(
        "us",
        description="Audible country code (e.g., 'us', 'de', 'uk')",
    )


class AuthStartResponse(BaseModel):
    """Response containing the Audible login URL."""

    login_url: str


class AuthCompleteRequest(BaseModel):
    """Request to complete Audible authentication."""

    redirect_url: str
