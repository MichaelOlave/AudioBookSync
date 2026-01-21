"""Storage configuration schemas."""

from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class StorageProvider(BaseModel):
    """Storage provider configuration."""

    provider_type: Literal["minio", "aws_s3", "gcs"] = Field(
        default="minio",
        description="Type of storage provider",
        json_schema_extra={"example": "minio"},
    )
    endpoint: str = Field(
        ...,
        description="Storage endpoint URL or address",
        json_schema_extra={"example": "http://localhost:9000"},
    )
    bucket_name: str = Field(
        ...,
        description="Bucket or container name for storing audiobooks",
        json_schema_extra={"example": "audiobooks"},
    )
    access_key: Optional[str] = Field(
        default=None,
        description="Access key or username for authentication (not returned in responses)",
    )
    secret_key: Optional[str] = Field(
        default=None,
        description="Secret key or password for authentication (not returned in responses)",
    )
    use_ssl: bool = Field(
        default=False,
        description="Whether to use SSL/TLS for connection",
    )
    region: Optional[str] = Field(
        default=None,
        description="AWS region (for S3 only)",
        json_schema_extra={"example": "us-east-1"},
    )


class StorageConfigResponse(BaseModel):
    """Response with current storage configuration."""

    user_id: str = Field(
        ...,
        description="User UUID",
    )
    provider_type: Literal["minio", "aws_s3", "gcs"] = Field(
        ...,
        description="Type of storage provider",
    )
    endpoint: str = Field(
        ...,
        description="Storage endpoint URL or address",
    )
    bucket_name: str = Field(
        ...,
        description="Bucket name",
    )
    use_ssl: bool = Field(
        default=False,
        description="Whether SSL/TLS is enabled",
    )
    is_connected: bool = Field(
        default=False,
        description="Whether storage is currently connected and healthy",
    )
    message: Optional[str] = Field(
        default=None,
        description="Additional status message",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "provider_type": "minio",
                "endpoint": "http://localhost:9000",
                "bucket_name": "audiobooks",
                "use_ssl": False,
                "is_connected": True,
                "message": "Storage is configured and healthy",
            }
        }
    )


class StorageConfigRequest(BaseModel):
    """Request to update storage configuration."""

    provider_type: Literal["minio", "aws_s3", "gcs"] = Field(
        default="minio",
        description="Type of storage provider",
    )
    endpoint: str = Field(
        ...,
        description="Storage endpoint URL or address",
    )
    bucket_name: str = Field(
        ...,
        description="Bucket or container name",
    )
    access_key: Optional[str] = Field(
        default=None,
        description="Access key or username",
    )
    secret_key: Optional[str] = Field(
        default=None,
        description="Secret key or password",
    )
    use_ssl: bool = Field(
        default=False,
        description="Whether to use SSL/TLS",
    )
    region: Optional[str] = Field(
        default=None,
        description="AWS region (for S3 only)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider_type": "minio",
                "endpoint": "http://localhost:9000",
                "bucket_name": "audiobooks",
                "access_key": "minioadmin",
                "secret_key": "minioadmin",
                "use_ssl": False,
            }
        }
    )


class StorageTestResponse(BaseModel):
    """Response from storage connection test."""

    success: bool = Field(
        ...,
        description="Whether connection test succeeded",
    )
    message: str = Field(
        ...,
        description="Test result message",
    )
    bucket_exists: Optional[bool] = Field(
        default=None,
        description="Whether the bucket exists",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if test failed",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Storage connection successful",
                "bucket_exists": True,
                "error": None,
            }
        }
    )
