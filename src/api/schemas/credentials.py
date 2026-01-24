"""Audible authentication credentials schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuthSessionData(BaseModel):
    """Temporary data for an Audible authentication session."""

    country_code: str
    code_verifier: str
    serial: str


class AudibleAuthJsonRequest(BaseModel):
    """Request with Audible auth.json content."""

    auth_json: Dict[str, Any] = Field(
        ...,
        description="Audible auth.json content (JSON object)",
        json_schema_extra={
            "example": {
                "access_token": "...",  # nosec B105
                "refresh_token": "...",  # nosec B105
                "expires_in": 3600,
                "created_at": 1703100000,
                "device_info": {"device_name": "Desktop"},
                "customer_info": {"customer_id": "amzn-123"},
            }
        },
    )
    activation_bytes: Optional[str] = Field(
        default=None,
        description="DRM activation bytes (hex string)",
        json_schema_extra={"example": "1f2e3d4c5b6a7988"},
    )

    @field_validator("auth_json")
    @classmethod
    def validate_auth_json(cls, v):
        """Validate required fields in auth.json."""
        required_fields = ["access_token", "refresh_token"]
        missing = [f for f in required_fields if f not in v]
        if missing:
            raise ValueError(f"Missing required fields in auth.json: {missing}")
        return v


class AudibleCredentialsResponse(BaseModel):
    """Response with Audible authentication credentials."""

    user_id: str = Field(
        ...,
        description="User UUID",
    )
    audible_email: Optional[str] = Field(
        default=None,
        description="Audible account email from customer_info",
    )
    device_name: Optional[str] = Field(
        default=None,
        description="Device name from auth.json",
    )
    has_access_token: bool = Field(
        default=False,
        description="Whether access token is stored",
    )
    has_activation_bytes: bool = Field(
        default=False,
        description="Whether activation bytes are stored",
    )
    auth_configured: bool = Field(
        default=False,
        description="Whether Audible authentication is fully configured",
    )
    auth_json_raw: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw auth.json data (tokens redacted for security)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "audible_email": "user@example.com",
                "device_name": "Desktop",
                "has_access_token": True,  # nosec B105
                "has_activation_bytes": True,  # nosec B105
                "auth_configured": True,  # nosec B105
                "auth_json_raw": {
                    "access_token": "****REDACTED****",  # nosec B105
                    "refresh_token": "****REDACTED****",  # nosec B105
                    "device_info": {"device_name": "Desktop"},
                },
            }
        }
    )


class AudibleCredentialsUpdate(BaseModel):
    """Response after updating credentials."""

    message: str = Field(
        ...,
        description="Status message",
    )
    auth_configured: bool = Field(
        ...,
        description="Whether auth is now configured",
    )
    auth_file_path: Optional[str] = Field(
        default=None,
        description="Path to auth file",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Audible credentials updated successfully",
                "auth_configured": True,
                "auth_file_path": "/home/user/.audible/auth.json",
            }
        }
    )
