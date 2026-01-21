"""User settings and Audible credentials endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from urllib.parse import urlparse

from ...database.db_users import user_ops
from ..security.auth import get_current_user
from ..middleware.error_handler import AuthenticationError, InternalServerError, handle_route_errors
from ..schemas.credentials import (
    AudibleCredentialsResponse,
    AudibleCredentialsUpdate,
)
from ..schemas.storage import (
    StorageConfigResponse,
    StorageConfigRequest,
    StorageTestResponse,
)

router = APIRouter()


def normalize_endpoint(endpoint: str) -> str:
    """
    Normalize storage endpoint by removing protocol prefix.

    MinIO SDK expects endpoint without protocol (e.g., "localhost:9000" instead of "http://localhost:9000").
    The protocol is determined by the `secure` parameter.

    Args:
        endpoint: Storage endpoint URL (may include protocol)

    Returns:
        Normalized endpoint without protocol
    """
    if not endpoint:
        return endpoint

    # Try to parse as URL to extract host:port
    try:
        if "://" in endpoint:
            parsed = urlparse(endpoint)
            # Reconstruct as host:port only
            netloc = parsed.netloc
            if parsed.port:
                return f"{parsed.hostname}:{parsed.port}"
            return netloc
        return endpoint
    except Exception:
        # If parsing fails, return as-is
        return endpoint


@router.get(
    "/audible-credentials",
    response_model=AudibleCredentialsResponse,
    summary="Get Audible credentials",
    description="Retrieve current user's Audible authentication configuration",
    responses={
        200: {"description": "Credentials retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("get Audible credentials")
async def get_audible_credentials(
    current_user: dict = Depends(get_current_user),
) -> AudibleCredentialsResponse:
    """
    Get the current user's Audible authentication credentials.

    Returns whether auth is configured and some non-sensitive metadata.
    Note: Tokens and activation bytes are never returned for security.

    Args:
        current_user: Current authenticated user (from JWT token)

    Returns:
        AudibleCredentialsResponse: User's Audible configuration status

    Example:
        GET /api/v1/settings/audible-credentials
        Authorization: Bearer ACCESS_TOKEN

        Response:
        {
            "user_id": "uuid-123",
            "auth_configured": true,
            "audible_email": "user@example.com",
            "device_name": "Desktop",
            "has_access_token": true,
            "has_activation_bytes": true
        }
    """
    user_id = str(current_user.user_id)
    if not user_id:
        raise AuthenticationError("Invalid user authentication")
    logger.info(f"Getting Audible credentials for user {user_id}")

    # Get user from database to ensure fresh data
    user = user_ops.get_user_by_id(user_id)
    if not user:
        raise InternalServerError("User not found")

    auth_configured = getattr(user, "audible_auth_json", None) is not None

    logger.info(
        f"Retrieved credentials for user {user_id}: "
        f"configured={auth_configured}, email={getattr(user, 'audible_email', None)}"
    )

    return AudibleCredentialsResponse(
        user_id=user_id,
        audible_email=getattr(user, "audible_email", None),
        device_name=getattr(user, "audible_device_name", None),
        has_access_token=getattr(user, "audible_auth_json", None) is not None,
        has_activation_bytes=getattr(user, "activation_bytes", None) is not None,
        auth_configured=auth_configured,
        auth_json_raw=None,  # Ensure raw data is not sen
    )


@router.delete(
    "/audible-credentials",
    response_model=AudibleCredentialsUpdate,
    status_code=status.HTTP_200_OK,
    summary="Clear Audible credentials",
    description="Remove stored Audible authentication configuration",
    responses={
        200: {"description": "Credentials cleared successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("clear Audible credentials")
async def clear_audible_credentials(
    current_user: dict = Depends(get_current_user),
) -> AudibleCredentialsUpdate:
    """
    Clear/remove the current user's Audible authentication credentials.

    This will disconnect the user's Audible account from AudioBookSync.
    Syncing will not be possible until credentials are re-added via the
    authentication flow.

    Args:
        current_user: Current authenticated user (from JWT token)

    Returns:
        AudibleCredentialsUpdate: Confirmation of clearance

    Example:
        DELETE /api/v1/settings/audible-credentials
        Authorization: Bearer ACCESS_TOKEN

        Response:
        {
            "message": "Audible credentials cleared successfully",
            "auth_configured": false,
            "auth_file_path": null
        }
    """
    user_id = str(current_user.user_id)
    if not user_id:
        raise AuthenticationError("Invalid user authentication")
    logger.info(f"Clearing Audible credentials for user {user_id}")

    # Clear credentials in database using the new dedicated function
    success = user_ops.clear_audible_auth(user_id)

    if not success:
        logger.error(f"Failed to clear credentials for user {user_id}")
        raise InternalServerError("Failed to clear credentials")

    logger.info(f"Successfully cleared credentials for user {user_id}")

    return AudibleCredentialsUpdate(
        message="Audible credentials cleared successfully",
        auth_configured=False,
        auth_file_path=None,
    )


@router.get(
    "/storage",
    response_model=StorageConfigResponse,
    summary="Get storage configuration",
    description="Retrieve current user's storage provider configuration",
    responses={
        200: {"description": "Storage configuration retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("get storage configuration")
async def get_storage_config(
    current_user: dict = Depends(get_current_user),
) -> StorageConfigResponse:
    """
    Get the current user's storage provider configuration.

    Returns the configured storage provider details without sensitive credentials.

    Args:
        current_user: Current authenticated user (from JWT token)

    Returns:
        StorageConfigResponse: User's storage configuration

    Example:
        GET /api/v1/settings/storage
        Authorization: Bearer ACCESS_TOKEN

        Response:
        {
            "user_id": "uuid-123",
            "provider_type": "minio",
            "endpoint": "http://localhost:9000",
            "bucket_name": "audiobooks",
            "use_ssl": false,
            "is_connected": true,
            "message": "Storage is configured and healthy"
        }
    """
    user_id = str(current_user.user_id)
    if not user_id:
        raise AuthenticationError("Invalid user authentication")
    logger.info(f"Getting storage configuration for user {user_id}")

    # Get storage config from user data (or use defaults)
    storage_config = getattr(current_user, "storage_config", None) or {}
    provider_type = storage_config.get("provider_type", "minio") if isinstance(storage_config, dict) else "minio"
    endpoint = storage_config.get("endpoint", "http://localhost:9000") if isinstance(storage_config, dict) else "http://localhost:9000"
    bucket_name = storage_config.get("bucket_name", "audiobooks") if isinstance(storage_config, dict) else "audiobooks"
    use_ssl = storage_config.get("use_ssl", False) if isinstance(storage_config, dict) else False

    # Test if storage is connected
    is_connected = False
    message = "Storage not configured"
    try:
        from ...infrastructure.minio_client import MinIOClient

        # Normalize endpoint for MinIO client
        normalized_endpoint = normalize_endpoint(endpoint) if endpoint else None

        if normalized_endpoint:
            client = MinIOClient(
                endpoint=normalized_endpoint,
                secure=use_ssl,
            )
        else:
            client = MinIOClient()

        client.bucket_exists(bucket_name)
        is_connected = True
        message = "Storage is configured and healthy"
    except Exception as e:
        logger.debug(f"Storage connection test failed: {e}")
        message = f"Storage connection failed: {str(e)}"

    logger.info(
        f"Retrieved storage config for user {user_id}: provider={provider_type}"
    )

    return StorageConfigResponse(
        user_id=user_id,
        provider_type=provider_type,
        endpoint=endpoint,
        bucket_name=bucket_name,
        use_ssl=use_ssl,
        is_connected=is_connected,
        message=message,
    )


@router.put(
    "/storage",
    response_model=StorageConfigResponse,
    summary="Update storage configuration",
    description="Update current user's storage provider configuration",
    responses={
        200: {"description": "Storage configuration updated successfully"},
        401: {"description": "Not authenticated"},
        400: {"description": "Invalid configuration"},
    },
)
@handle_route_errors("update storage configuration")
async def update_storage_config(
    config: StorageConfigRequest,
    current_user: dict = Depends(get_current_user),
) -> StorageConfigResponse:
    """
    Update the current user's storage provider configuration.

    Allows changing the storage provider type, endpoint, and credentials.

    Args:
        config: New storage configuration
        current_user: Current authenticated user (from JWT token)

    Returns:
        StorageConfigResponse: Updated storage configuration

    Example:
        PUT /api/v1/settings/storage
        Authorization: Bearer ACCESS_TOKEN

        Request:
        {
            "provider_type": "minio",
            "endpoint": "http://localhost:9000",
            "bucket_name": "audiobooks",
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "use_ssl": false
        }

        Response:
        {
            "user_id": "uuid-123",
            "provider_type": "minio",
            "endpoint": "http://localhost:9000",
            "bucket_name": "audiobooks",
            "use_ssl": false,
            "is_connected": true,
            "message": "Storage configuration updated successfully"
        }
    """
    user_id = str(current_user.user_id)
    if not user_id:
        raise AuthenticationError("Invalid user authentication")

    logger.info(f"Updating storage configuration for user {user_id}")

    # Validate endpoint is not empty
    if not config.endpoint or not config.bucket_name:
        raise InternalServerError("Endpoint and bucket name are required")

    # Update user storage config in database
    storage_config = {
        "provider_type": config.provider_type,
        "endpoint": config.endpoint,
        "bucket_name": config.bucket_name,
        "access_key": config.access_key,
        "secret_key": config.secret_key,
        "use_ssl": config.use_ssl,
        "region": config.region,
    }

    success = user_ops.update_user_storage_config(user_id, storage_config)

    if not success:
        logger.error(f"Failed to update storage config for user {user_id}")
        raise InternalServerError("Failed to update storage configuration")

    # Test if new storage is connected
    is_connected = False
    message = "Storage configuration updated"
    try:
        from ...infrastructure.minio_client import MinIOClient

        # Normalize endpoint for MinIO client
        normalized_endpoint = normalize_endpoint(config.endpoint)

        client = MinIOClient(
            endpoint=normalized_endpoint,
            access_key=config.access_key or "minioadmin",
            secret_key=config.secret_key or "minioadmin",
            secure=config.use_ssl,
        )
        client.bucket_exists(config.bucket_name)
        is_connected = True
        message = "Storage configuration updated and connected successfully"
    except Exception as e:
        logger.debug(f"Storage connection test failed after update: {e}")
        message = f"Storage configuration updated but connection test failed: {str(e)}"

    logger.info(
        f"Successfully updated storage config for user {user_id}: provider={config.provider_type}"
    )

    return StorageConfigResponse(
        user_id=user_id,
        provider_type=config.provider_type,
        endpoint=config.endpoint,
        bucket_name=config.bucket_name,
        use_ssl=config.use_ssl,
        is_connected=is_connected,
        message=message,
    )


@router.post(
    "/storage/test",
    response_model=StorageTestResponse,
    summary="Test storage connection",
    description="Test connection to the configured storage provider",
    responses={
        200: {"description": "Connection test completed"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("test storage connection")
async def test_storage_connection(
    config: StorageConfigRequest,
    current_user: dict = Depends(get_current_user),
) -> StorageTestResponse:
    """
    Test the connection to the configured storage provider.

    Verifies that the storage provider is accessible and the bucket exists.

    Args:
        config: Storage configuration to test
        current_user: Current authenticated user (from JWT token)

    Returns:
        StorageTestResponse: Test result

    Example:
        POST /api/v1/settings/storage/test
        Authorization: Bearer ACCESS_TOKEN

        Request:
        {
            "provider_type": "minio",
            "endpoint": "http://localhost:9000",
            "bucket_name": "audiobooks",
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "use_ssl": false
        }

        Response:
        {
            "success": true,
            "message": "Storage connection successful",
            "bucket_exists": true,
            "error": null
        }
    """
    user_id = str(current_user.user_id)
    if not user_id:
        raise AuthenticationError("Invalid user authentication")

    logger.info(f"Testing storage connection for user {user_id} with provider {config.provider_type}")

    try:
        from ...infrastructure.minio_client import MinIOClient

        # Normalize endpoint (remove protocol prefix)
        normalized_endpoint = normalize_endpoint(config.endpoint)

        # Create client with the provided configuration
        client = MinIOClient(
            endpoint=normalized_endpoint,
            access_key=config.access_key or "minioadmin",
            secret_key=config.secret_key or "minioadmin",
            secure=config.use_ssl,
        )
        bucket_exists = client.bucket_exists(config.bucket_name)

        logger.info(
            f"Storage connection test successful for user {user_id}: bucket_exists={bucket_exists}"
        )

        return StorageTestResponse(
            success=True,
            message="Storage connection successful",
            bucket_exists=bucket_exists,
            error=None,
        )

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Storage connection test failed for user {user_id}: {error_msg}")

        return StorageTestResponse(
            success=False,
            message="Storage connection failed",
            bucket_exists=False,
            error=error_msg,
        )
