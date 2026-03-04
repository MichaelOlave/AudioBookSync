"""User database service layer using SQLAlchemy ORM."""

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional, Union
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.family import Family
from src.database.models.user import User
from src.database.services.base_service import delete_entity, get_by_id, update_entity

if TYPE_CHECKING:
    from src.ports.file_storage_port import FileStoragePort


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    auth_file_path: Optional[str] = None,
    activation_bytes: Optional[str] = None,
    password_hash: Optional[str] = None,
) -> Optional[User]:
    """Create a new user.

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


async def create_family(
    db: AsyncSession,
    name: Optional[str],
    owner_user_id: Optional[Union[str, UUID]] = None,
) -> Optional[Family]:
    """Create a new family.

    Args:
        db: Database session
        name: Optional family name

    Returns:
        Created Family object if successful, None otherwise
    """
    try:
        family = Family(name=name, owner_user_id=owner_user_id)
        db.add(family)
        await db.flush()
        await db.refresh(family)
        logger.info(f"Created family: {family.family_id}")
        return family
    except Exception as e:
        logger.error(f"Family creation failed: {e}")
        return None


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by ID.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        User object if found, None otherwise
    """
    return await get_by_id(db, User, user_id, id_column="user_id")


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username.

    Args:
        db: Database session
        username: User's username

    Returns:
        User object if found, None otherwise
    """
    try:
        logger.info(username)
        result = await db.execute(select(User).where(User.username == username))
        logger.info(result)
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get user by username: {e}")
        return None


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email.

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


async def get_family_members(db: AsyncSession, family_id: Union[str, UUID]) -> list[User]:
    """Get all members of a family.

    Args:
        db: Database session
        family_id: Family UUID

    Returns:
        List of User objects
    """
    try:
        result = await db.execute(
            select(User).where(User.family_id == family_id).order_by(User.username)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get family members: {e}")
        return []


async def get_user_by_audible_email(db: AsyncSession, audible_email: str) -> Optional[User]:
    """Get user by Audible email.

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
    """Update user's password hash.

    Args:
        db: Database session
        user_id: User's UUID
        password_hash: New password hash

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    return await update_entity(db, user, {"password_hash": password_hash}, entity_id=user_id)


async def get_family_by_id(db: AsyncSession, family_id: str) -> Optional[Family]:
    """Get family by ID.

    Args:
        db: Database session
        family_id: Family UUID

    Returns:
        Family object if found, None otherwise
    """
    return await get_by_id(db, Family, family_id, id_column="family_id")


async def update_family(
    db: AsyncSession,
    family_id: str,
    updates: Dict[str, Any],
) -> Optional[Family]:
    """Update a family's fields.

    Args:
        db: Database session
        family_id: Family UUID
        updates: Fields to update

    Returns:
        Updated Family object if successful, None otherwise
    """
    family = await get_family_by_id(db, family_id)
    success = await update_entity(db, family, updates, entity_id=family_id)
    if not success:
        return None
    return family


async def delete_family(db: AsyncSession, family_id: str) -> bool:
    """Delete a family.

    Args:
        db: Database session
        family_id: Family UUID

    Returns:
        True if successful, False otherwise
    """
    family = await get_family_by_id(db, family_id)
    return await delete_entity(db, family, entity_id=family_id)


async def update_user_family_settings(
    db: AsyncSession,
    user_id: str,
    updates: Dict[str, Any],
) -> Optional[User]:
    """Update user's family membership and sharing settings.

    Args:
        db: Database session
        user_id: User's UUID
        updates: Fields to update (family_id, share_library_with_family)

    Returns:
        Updated User object if successful, None otherwise
    """
    user = await get_user_by_id(db, user_id)
    success = await update_entity(db, user, updates, entity_id=user_id)
    if not success:
        return None
    return user


async def get_accessible_user_ids(
    db: AsyncSession,
    user_id: str,
    family_id: Optional[Union[str, UUID]],
) -> list[str]:
    """Get list of user IDs whose books are visible to the current user.

    Includes the current user and any family members who share their libraries.
    """
    user_ids = [user_id]
    if not family_id:
        return user_ids

    try:
        result = await db.execute(
            select(User.user_id).where(
                User.family_id == family_id,
                User.share_library_with_family.is_(True),
            )
        )
        shared_ids = [str(shared_id) for shared_id in result.scalars().all()]
        for shared_id in shared_ids:
            if shared_id not in user_ids:
                user_ids.append(shared_id)
    except Exception as e:
        logger.error(f"Failed to get accessible user IDs: {e}")

    return user_ids


async def update_user_email(db: AsyncSession, user_id: str, email: str) -> bool:
    """Update user's email address.

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
    """Update user's last sync timestamp.

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
    """Update user's Audible authentication information.

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
    """Update user's Audible activation bytes.

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
    """Get all active users.

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
    """Deactivate a user account.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        True if successful, False otherwise
    """
    user = await get_user_by_id(db, user_id)
    return await update_entity(db, user, {"is_active": False}, entity_id=user_id)


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """Delete a user account (cascades to related records).

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
    """Update Audible auth.json with field extraction.

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
    """Clear all Audible authentication fields.

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
    """Get Audible auth.json with optional sensitive token redaction.

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
                auth_json["access_token"] = "REDACTED"  # nosec B105
            if "refresh_token" in auth_json:
                auth_json["refresh_token"] = "REDACTED"  # nosec B105
            if "private_key" in auth_json:
                auth_json["private_key"] = "REDACTED"  # nosec B105

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
    """Update user's storage configuration as JSON.

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

        user.storage_config = storage_config
        await db.flush()
        logger.info(f"Updated storage config for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to update storage config: {e}")
        return False


async def get_user_storage_adapter(
    db: AsyncSession,
    user_id: str,
) -> "FileStoragePort":
    """Get storage adapter instance for a user based on their configuration.

    Retrieves the user's storage provider preference from the database and
    returns an instantiated storage adapter ready to use.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        FileStoragePort: Configured storage adapter for the user

    Raises:
        ValueError: If user not found or storage config is invalid
        ImportError: If required storage adapter dependencies are missing

    Example:
        >>> storage = await get_user_storage_adapter(db, user_id)
        >>> success, key = storage.save_file(
        ...     user_id=user_id,
        ...     file_path="/path/to/file.aax",
        ...     file_type="downloaded",
        ...     asin="B001ABC123"
        ... )
    """
    from src.adapters.storage.storage_factory import get_storage_adapter
    from src.ports.file_storage_port import FileStoragePort

    try:
        user = await get_user_by_id(db, user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Get storage config from user
        storage_config = user.storage_config or {}

        # Default to MinIO if no config set
        provider_type = storage_config.get("provider_type", "minio")

        logger.info(f"Getting storage adapter for user {user_id}: provider={provider_type}")

        # Get adapter from factory
        adapter = get_storage_adapter(provider_type, storage_config)

        logger.debug(f"Successfully created {provider_type} adapter for user {user_id}")
        return adapter

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to get storage adapter for user {user_id}: {e}")
        raise ValueError(f"Failed to initialize storage adapter: {e}")
