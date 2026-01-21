"""Authentication-related utility functions."""

from typing import Optional, Any, Union
from loguru import logger


def get_user_id(current_user: Any) -> str:
    """
    Extract user_id from current_user object as a string.

    Handles both SQLAlchemy model objects (from get_current_user dependency)
    and dictionary representations consistently.

    Args:
        current_user: User object/dict from get_current_user dependency

    Returns:
        User ID as string

    Raises:
        AttributeError: If user_id cannot be extracted
    """
    if hasattr(current_user, "user_id"):
        # SQLAlchemy model object
        return str(current_user.user_id)
    elif isinstance(current_user, dict):
        # Dictionary representation
        user_id = current_user.get("user_id")
        if user_id is None:
            raise AttributeError("user_id not found in current_user dict")
        return str(user_id)
    else:
        raise AttributeError(f"Cannot extract user_id from {type(current_user)}")


def normalize_activation_bytes(raw_bytes: object) -> Optional[str]:
    """Convert activation bytes value to a hex string if possible."""
    if raw_bytes is None:
        return None

    try:
        if isinstance(raw_bytes, (bytes, bytearray)):
            return raw_bytes.hex()
        return str(raw_bytes)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(f"Failed to normalize activation bytes: {exc}")
        return None
