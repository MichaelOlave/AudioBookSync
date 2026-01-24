"""User endpoints (profile, preferences, etc)."""

from typing import cast

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ...database.models.user import User
from ...database.services import user_service
from ..middleware.error_handler import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    InternalServerError,
    ResourceNotFoundError,
    ValidationError,
    handle_route_errors,
)
from ..schemas.common import MessageResponse
from ..schemas.user import (
    EmailChangeRequest,
    EmailChangeResponse,
    PasswordChangeRequest,
    UserFamilyUpdate,
    UserResponse,
)
from ..security.auth import get_current_user
from ..security.password import hash_password, verify_password

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieve the authenticated user's profile information",
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("fetch user profile")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Get the current authenticated user's profile information.

    This endpoint returns the profile data for the authenticated user,
    including username, email, account status, and timestamps.

    Args:
        current_user: Current authenticated user (from JWT token)
        db: Database session

    Returns:
        UserResponse: User profile data (without sensitive information)

    Raises:
        HTTPException: If user not found or not authenticated

    Example:
        GET /api/v1/users/me
        Headers:
            Authorization: Bearer <access_token>

        Response:
        {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "john_doe",
            "email": "john@example.com",
            "is_active": true,
            "family_id": null,
            "share_library_with_family": false,
            "last_sync_date": "2025-01-20T15:30:00",
            "created_at": "2025-01-15T10:00:00",
            "updated_at": "2025-01-20T15:30:00"
        }
    """
    logger.info(f"Fetching profile for user: {current_user.user_id}")

    # current_user is already fetched and validated by get_current_user dependency
    if not current_user.is_active:
        logger.warning(f"Inactive user profile access attempt: {current_user.user_id}")
        raise AuthorizationError("User account is inactive")

    logger.info(f"User profile retrieved successfully: {current_user.user_id}")
    return UserResponse.from_orm(current_user)


@router.patch(
    "/me/password",
    response_model=MessageResponse,
    summary="Change user password",
    description="Change the authenticated user's password with current password verification",
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Bad request (new password same as current)"},
        401: {"description": "Wrong current password"},
        422: {"description": "Validation error (weak password)"},
    },
)
@handle_route_errors("change user password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Change the authenticated user's password.

    Requires verification of current password before accepting new password.
    New password must meet strength requirements.

    Args:
        password_data: Current password and new password
        current_user: Current authenticated user (from JWT token)
        db: Database session

    Returns:
        MessageResponse: Success message

    Raises:
        AuthenticationError: If current password is incorrect
        HTTPException: If new password same as current or database error

    Example:
        PATCH /api/v1/users/me/password
        Headers:
            Authorization: Bearer <access_token>

        Body:
        {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword456!"
        }
    """
    logger.info(f"Password change request for user: {current_user.user_id}")

    # Verify current password
    current_password_hash = cast(str, current_user.password_hash)
    if not current_password_hash or not verify_password(
        password_data.current_password, current_password_hash
    ):
        logger.warning(
            f"Password change failed: Wrong current password for user: {current_user.user_id}"
        )
        raise AuthenticationError("Current password is incorrect")

    # Check new password is different from current
    if verify_password(password_data.new_password, current_password_hash):
        logger.warning(
            f"Password change failed: New password same as current for user: {current_user.user_id}"
        )
        raise AuthenticationError("New password must be different from current password")

    # Hash new password and update database
    new_password_hash = hash_password(password_data.new_password)
    success = await user_service.update_user_password(
        db, str(current_user.user_id), new_password_hash
    )

    if not success:
        logger.error(f"Failed to update password in database for user: {current_user.user_id}")
        raise InternalServerError("Failed to update password")

    await db.commit()
    logger.info(f"Password changed successfully for user: {current_user.user_id}")
    return MessageResponse(
        message="Password updated successfully",
        success=True,
    )


@router.patch(
    "/me/email",
    response_model=EmailChangeResponse,
    summary="Change user email",
    description="Change the authenticated user's email address with password verification",
    responses={
        200: {"description": "Email changed successfully"},
        400: {"description": "Bad request (new email same as current)"},
        401: {"description": "Wrong password"},
        409: {"description": "Email already in use by another user"},
        422: {"description": "Validation error (invalid email format)"},
    },
)
@handle_route_errors("change user email")
async def change_email(
    email_data: EmailChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EmailChangeResponse:
    """
    Change the authenticated user's email address.

    Requires password verification before accepting new email.
    New email must be unique and valid.

    Args:
        email_data: Current password and new email
        current_user: Current authenticated user (from JWT token)
        db: Database session

    Returns:
        EmailChangeResponse: Success message with new email

    Raises:
        AuthenticationError: If password is incorrect
        ConflictError: If email already in use
        HTTPException: If email same as current or database error

    Example:
        PATCH /api/v1/users/me/email
        Headers:
            Authorization: Bearer <access_token>

        Body:
        {
            "password": "CurrentPassword123!",
            "new_email": "newemail@example.com"
        }
    """
    logger.info(f"Email change request for user: {current_user.user_id}")

    # Verify password
    current_password_hash = cast(str, current_user.password_hash)
    if not current_password_hash or not verify_password(email_data.password, current_password_hash):
        logger.warning(f"Email change failed: Wrong password for user: {current_user.user_id}")
        raise AuthenticationError("Password is incorrect")

    # Check new email is different from current
    if email_data.new_email.lower() == current_user.email.lower():
        logger.warning(
            f"Email change failed: New email same as current for user: {current_user.user_id}"
        )
        raise AuthenticationError("New email must be different from current email")

    # Check if email is already in use by another user
    existing_user = await user_service.get_user_by_email(db, email_data.new_email)
    if existing_user:
        logger.warning(f"Email change failed: Email already in use: {email_data.new_email}")
        raise ConflictError(f"Email '{email_data.new_email}' is already in use")

    # Update email in database
    success = await user_service.update_user_email(
        db, str(current_user.user_id), email_data.new_email
    )

    if not success:
        logger.error(f"Failed to update email in database for user: {current_user.user_id}")
        raise InternalServerError("Failed to update email")

    await db.commit()
    logger.info(f"Email changed successfully for user: {current_user.user_id}")
    return EmailChangeResponse(
        message="Email updated successfully",
        success=True,
        email=email_data.new_email,
    )


@router.patch(
    "/me/family",
    response_model=UserResponse,
    summary="Update family settings",
    description="Update family membership and sharing preferences",
    responses={
        200: {"description": "Family settings updated successfully"},
        422: {"description": "Invalid update payload"},
        401: {"description": "Not authenticated"},
        404: {"description": "Family not found"},
    },
)
@handle_route_errors("update family settings")
async def update_family_settings(
    payload: UserFamilyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Update family membership and sharing preferences.

    Allows the user to join/leave a family and toggle library sharing.
    """
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise ValidationError("Provide at least one family setting to update")

    if "family_id" in updates and current_user.family_id:
        family = await user_service.get_family_by_id(db, str(current_user.family_id))
        if (
            family
            and family.owner_user_id
            and str(family.owner_user_id) == str(current_user.user_id)
        ):
            new_family_id = updates.get("family_id")
            if new_family_id is None or str(new_family_id) != str(current_user.family_id):
                raise ValidationError("Family head cannot leave the family")

    if "family_id" in updates and updates["family_id"] is not None:
        family = await user_service.get_family_by_id(db, str(updates["family_id"]))
        if not family:
            raise ResourceNotFoundError("Family not found")

    updated_user = await user_service.update_user_family_settings(
        db,
        str(current_user.user_id),
        updates,
    )
    if not updated_user:
        raise InternalServerError("Failed to update family settings")

    await db.commit()
    await db.refresh(updated_user)
    return UserResponse.from_orm(updated_user)
