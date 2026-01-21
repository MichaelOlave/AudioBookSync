"""User database service layer using SQLAlchemy ORM."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import User
from src.database.services.base_service import delete_entity, get_by_id, update_entity


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    auth_file_path: Optional[str] = None,
    activation_bytes: Optional[str] = None,
    password_hash: Optional[str] = None,
) -> Optional[User]:
    """
    Create a new user.

    Args:
        db: Database session
        username: User's username
        email: User's email address
        auth_file_path: Path to Audible authentication file
        activation_bytes: DRM activation bytes
        password_hash: Hashed password for API authentication

    Returns:
        Created User object if successful, None otherwise
    """
    try:
        user = User(
            username=username,
            email=email,
            auth_file_path=auth_file_path,
            activation_bytes=activation_bytes,
            password_hash=password_hash,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info(f"Created user: {username} (ID: {user.user_id})")
        return user
    except Exception as e:
        logger.error(f"User creation failed: {e}")
        return None


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    Get user by ID.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        User object if found, None otherwise
    """
    return await get_by_id(db, User, user_id, id_column="user_id")


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Get user by username.

    Args:
        db: Database session
        username: User's username

    Returns:
        User object if found, None otherwise
    """
    try:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get user by username: {e}")
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email.

    Args:
        db: Database session
        email: User's email address

    Returns:
        User object if found, None otherwise
    """
    try:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get user by email: {e}")
        return None


async def get_user_by_audible_email(db: AsyncSession, audible_email: str) -> Optional[User]:
    """
    Get user by Audible email.

    Args:
        db: Database session
        audible_email: Audible account email

    Returns:
        User object if found, None otherwise
    """
    try:
        result = await db.execute(select(User).where(User.audible_email == audible_email))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get user by Audible email: {e}")
        return None


async def update_user_password(db: AsyncSession, user_id: str, password_hash: str) -> bool:
    """
    Update user's password hash.

    Args:
        db: Database session
        user_id: User's UUID
        password_hash: New password hash

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    return await update_entity(db, user, {"password_hash": password_hash}, entity_id=user_id)


async def update_user_email(db: AsyncSession, user_id: str, email: str) -> bool:
    """
    Update user's email address.

    Args:
        db: Database session
        user_id: User's UUID
        email: New email address

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    return await update_entity(db, user, {"email": email}, entity_id=user_id)


async def update_user_last_sync(db: AsyncSession, user_id: str) -> bool:
    """
    Update user's last sync timestamp.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    return await update_entity(
        db, user, {"last_sync_date": datetime.now(timezone.utc)}, entity_id=user_id
    )


async def update_user_audible_auth(
    db: AsyncSession,
    user_id: str,
    audible_auth_json: Optional[str] = None,
    audible_email: Optional[str] = None,
    audible_device_name: Optional[str] = None,
) -> bool:
    """
    Update user's Audible authentication information.

    Args:
        db: Database session
        user_id: User's UUID
        audible_auth_json: Parsed auth.json as JSON string
        audible_email: Audible account email
        audible_device_name: Device name from Audible

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    updates = {}
    if audible_auth_json is not None:
        updates["audible_auth_json"] = audible_auth_json
    if audible_email is not None:
        updates["audible_email"] = audible_email
    if audible_device_name is not None:
        updates["audible_device_name"] = audible_device_name

    if not updates:
        return True

    return await update_entity(db, user, updates, entity_id=user_id)


async def update_user_activation_bytes(
    db: AsyncSession, user_id: str, activation_bytes: str
) -> bool:
    """
    Update user's Audible activation bytes.

    Args:
        db: Database session
        user_id: User's UUID
        activation_bytes: DRM activation bytes

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    return await update_entity(db, user, {"activation_bytes": activation_bytes}, entity_id=user_id)


async def get_active_users(db: AsyncSession) -> list[User]:
    """
    Get all active users.

    Args:
        db: Database session

    Returns:
        List of active User objects
    """
    try:
        result = await db.execute(select(User).where(User.is_active))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get active users: {e}")
        return []


async def deactivate_user(db: AsyncSession, user_id: str) -> bool:
    """
    Deactivate a user account.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    return await update_entity(db, user, {"is_active": False}, entity_id=user_id)


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """
    Delete a user account (cascades to related records).

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    return await delete_entity(db, user, entity_id=user_id)


async def update_audible_auth_json(
    db: AsyncSession,
    user_id: str,
    auth_json: Dict[str, Any],
    activation_bytes: Optional[str] = None,
) -> bool:
    """
    Update Audible auth.json with field extraction.

    Extracts commonly used fields from nested JSON and stores them
    in dedicated columns for quick access.

    Args:
        db: Database session
        user_id: User's UUID
        auth_json: Dictionary containing Audible auth.json content
        activation_bytes: Optional DRM activation bytes

    Returns:
        True if successful, False otherwise
    """
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            logger.warning(f"User not found for auth update: {user_id}")
            return False

        # Extract commonly used fields from nested JSON
        audible_email = None
        device_name = None

        if "customer_info" in auth_json:
            audible_email = auth_json["customer_info"].get("account_email")
        if "device_info" in auth_json:
            device_name = auth_json["device_info"].get("device_name")

        # Store as JSON string (TEXT column compatibility)
        auth_json_str = json.dumps(auth_json)

        # Update all fields atomically
        user.audible_auth_json = auth_json_str
        user.audible_email = audible_email
        user.audible_device_name = device_name
        if activation_bytes:
            user.activation_bytes = activation_bytes

        await db.flush()
        logger.info(f"Updated Audible auth for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update Audible auth: {e}")
        return False


async def clear_audible_auth(db: AsyncSession, user_id: str) -> bool:
    """
    Clear all Audible authentication fields.

    Sets all Audible-related fields to None.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            logger.warning(f"User not found for auth clear: {user_id}")
            return False

        user.audible_auth_json = None
        user.audible_email = None
        user.audible_device_name = None
        user.activation_bytes = None
        user.auth_file_path = None

        await db.flush()
        logger.info(f"Cleared Audible auth for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear Audible auth: {e}")
        return False


async def get_audible_auth_json(
    db: AsyncSession,
    user_id: str,
    redact_secrets: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Get Audible auth.json with optional sensitive token redaction.

    Args:
        db: Database session
        user_id: User's UUID
        redact_secrets: Whether to redact sensitive tokens (default True)

    Returns:
        Dictionary containing Audible auth data, or None if not found
    """
    try:
        user = await get_user_by_id(db, user_id)
        if not user or not user.audible_auth_json:
            return None

        auth_json = json.loads(user.audible_auth_json)

        if redact_secrets:
            # Redact sensitive tokens
            if "access_token" in auth_json:
                auth_json["access_token"] = "REDACTED"
            if "refresh_token" in auth_json:
                auth_json["refresh_token"] = "REDACTED"
            if "private_key" in auth_json:
                auth_json["private_key"] = "REDACTED"

        logger.debug(f"Retrieved Audible auth for user: {user_id}")
        return auth_json
    except Exception as e:
        logger.error(f"Failed to get Audible auth: {e}")
        return None


async def update_user_storage_config(
    db: AsyncSession,
    user_id: str,
    storage_config: Dict[str, Any],
) -> bool:
    """
    Update user's storage configuration as JSON.

    Args:
        db: Database session
        user_id: User's UUID
        storage_config: Dictionary containing storage configuration

    Returns:
        True if successful, False otherwise
    """
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            logger.warning(f"User not found for storage config update: {user_id}")
            return False

        user.storage_config = json.dumps(storage_config)
        await db.flush()
        logger.info(f"Updated storage config for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update storage config: {e}")
        return False
