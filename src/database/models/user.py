"""User model for SQLAlchemy ORM."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    from src.database.models.book import Book


class User(Base):
    """User model mapped to users table."""

    __tablename__ = "users"

    user_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    auth_file_path = Column(String(500), nullable=True)
    activation_bytes = Column(String(16), nullable=True)
    audible_auth_json = Column(Text, nullable=True)
    audible_email = Column(String(255), nullable=True, index=True)
    audible_device_name = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_sync_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_current_timestamp, onupdate=get_current_timestamp, nullable=False)

    # Relationships
    books = relationship(
        "Book",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    sync_history = relationship(
        "SyncHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    error_logs = relationship(
        "ErrorLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, username={self.username}, email={self.email})>"
