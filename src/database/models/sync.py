"""Sync history model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    pass


class SyncHistory(Base):
    """SyncHistory model mapped to sync_history table."""

    __tablename__ = "sync_history"

    sync_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sync_type = Column(String(20), default="full", nullable=False)
    sync_started_at = Column(
        DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", nullable=False
    )
    sync_completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    books_found = Column(Integer, default=0)
    books_added = Column(Integer, default=0)
    books_removed = Column(Integer, default=0)
    books_downloaded = Column(Integer, default=0)
    books_decrypted = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    status = Column(String(20), default="in_progress", nullable=False, index=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")

    # Relationships
    user = relationship("User", back_populates="sync_history", lazy="select")

    def __repr__(self) -> str:
        """Return a debug representation."""
        return (
            f"<SyncHistory(sync_id={self.sync_id}, user_id={self.user_id}, status={self.status})>"
        )
