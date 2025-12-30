"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema for user registration request."""

    username: str = Field(
        min_length=3,
        max_length=50,
        description="Username (3-50 characters)",
        example="john_doe",
    )
    email: EmailStr = Field(
        description="User's email address",
        example="john@example.com",
    )
    password: str = Field(
        min_length=8,
        max_length=100,
        description="Password (minimum 8 characters)",
    )


class UserLogin(BaseModel):
    """Schema for user login request (OAuth2 compatible)."""

    username: str = Field(
        description="Username or email",
        example="john_doe",
    )
    password: str = Field(
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
