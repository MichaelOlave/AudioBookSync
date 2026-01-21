"""User database service layer using SQLAlchemy ORM."""

from typing import Optional
from datetime import datetime, timezone
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database.models.user import User


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
    try:
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get user by ID: {e}")
        return None


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
        result = await db.execute(
            select(User).where(User.username == username)
        )
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
        result = await db.execute(
            select(User).where(User.email == email)
        )
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
        result = await db.execute(
            select(User).where(User.audible_email == audible_email)
        )
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
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            return False

        user.password_hash = password_hash
        await db.flush()
        logger.info(f"Updated password for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update user password: {e}")
        return False


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
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            return False

        user.email = email
        await db.flush()
        logger.info(f"Updated email for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update user email: {e}")
        return False


async def update_user_last_sync(db: AsyncSession, user_id: str) -> bool:
    """
    Update user's last sync timestamp.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            return False

        user.last_sync_date = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"Updated last sync date for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update user last sync: {e}")
        return False


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
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            return False

        if audible_auth_json is not None:
            user.audible_auth_json = audible_auth_json
        if audible_email is not None:
            user.audible_email = audible_email
        if audible_device_name is not None:
            user.audible_device_name = audible_device_name

        await db.flush()
        logger.info(f"Updated Audible auth for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update Audible auth: {e}")
        return False


async def update_user_activation_bytes(db: AsyncSession, user_id: str, activation_bytes: str) -> bool:
    """
    Update user's Audible activation bytes.

    Args:
        db: Database session
        user_id: User's UUID
        activation_bytes: DRM activation bytes

    Returns:
        True if successful, False otherwise
    """
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            return False

        user.activation_bytes = activation_bytes
        await db.flush()
        logger.info(f"Updated activation bytes for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update activation bytes: {e}")
        return False


async def get_active_users(db: AsyncSession) -> list[User]:
    """
    Get all active users.

    Args:
        db: Database session

    Returns:
        List of active User objects
    """
    try:
        result = await db.execute(
            select(User).where(User.is_active == True)
        )
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
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            return False

        user.is_active = False
        await db.flush()
        logger.info(f"Deactivated user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to deactivate user: {e}")
        return False


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """
    Delete a user account (cascades to related records).

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            return False

        await db.delete(user)
        await db.flush()
        logger.info(f"Deleted user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        return False
