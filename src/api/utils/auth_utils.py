"""Authentication-related utility functions."""

from typing import Optional
from loguru import logger


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
