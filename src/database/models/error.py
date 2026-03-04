"""Error log model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    pass


class ErrorLog(Base):
    """ErrorLog model mapped to error_log table."""

    __tablename__ = "error_log"

    error_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    asin = Column(
        String(10), ForeignKey("books.asin", ondelete="SET NULL"), nullable=True, index=True
    )
    sync_id = Column(
        UUID(as_uuid=True), ForeignKey("sync_history.sync_id", ondelete="SET NULL"), nullable=True
    )
    error_type = Column(String(50), nullable=False, index=True)
    error_code = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=False)
    error_details = Column(JSON, nullable=True)
    stack_trace = Column(Text, nullable=True)
    severity = Column(String(20), default="error")
    timestamp = Column(
        DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", nullable=False, index=True
    )
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="error_logs", lazy="select")

    def __repr__(self) -> str:
        """Return a debug representation."""
        return f"<ErrorLog(error_id={self.error_id}, error_type={self.error_type}, severity={self.severity})>"
