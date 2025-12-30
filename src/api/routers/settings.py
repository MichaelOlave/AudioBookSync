"""User settings and Audible credentials endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from ...database.db_users import user_ops
from ..security.auth import get_current_user
from ..schemas.credentials import (
    AudibleCredentialsResponse,
    AudibleCredentialsUpdate,
)

router = APIRouter()


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
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )
        logger.info(f"Getting Audible credentials for user {user_id}")

        # Get user from database to ensure fresh data
        user = user_ops.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        auth_configured = user.get("audible_auth_json") is not None

        logger.info(
            f"Retrieved credentials for user {user_id}: "
            f"configured={auth_configured}, email={user.get('audible_email')}"
        )

        return AudibleCredentialsResponse(
            user_id=user_id,
            audible_email=user.get("audible_email"),
            device_name=user.get("audible_device_name"),
            has_access_token=user.get("audible_auth_json") is not None,
            has_activation_bytes=user.get("activation_bytes") is not None,
            auth_configured=auth_configured,
            auth_json_raw=None,  # Ensure raw data is not sen
        )

    except Exception as e:
        logger.error(
            f"Error getting credentials for user {current_user.get('user_id')}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credentials",
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
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )
        logger.info(f"Clearing Audible credentials for user {user_id}")

        # Clear credentials in database using the new dedicated function
        success = user_ops.clear_audible_auth(user_id)

        if not success:
            logger.error(f"Failed to clear credentials for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear credentials",
            )

        logger.info(f"Successfully cleared credentials for user {user_id}")

        return AudibleCredentialsUpdate(
            message="Audible credentials cleared successfully",
            auth_configured=False,
            auth_file_path=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error clearing credentials for user {current_user.get('user_id')}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear credentials",
        )
