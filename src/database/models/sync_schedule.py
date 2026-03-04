"""Sync schedule model for recurring Audible syncs."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp


class SyncSchedule(Base):
    """SyncSchedule model mapped to sync_schedules table."""

    __tablename__ = "sync_schedules"

    schedule_id = Column(
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
    interval_minutes = Column(Integer, nullable=False)
    action = Column(String(20), default="metadata_only", nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    user = relationship("User", back_populates="sync_schedules", lazy="select")

    def __repr__(self) -> str:
        """Return a debug representation."""
        return (
            f"<SyncSchedule(schedule_id={self.schedule_id}, user_id={self.user_id}, "
            f"interval_minutes={self.interval_minutes}, action={self.action}, enabled={self.enabled})>"
        )
