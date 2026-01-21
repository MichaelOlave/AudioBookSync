"""Base model and utilities for SQLAlchemy ORM models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID."""
    return uuid.uuid4()


def get_current_timestamp():
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)
