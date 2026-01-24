"""Download status model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class DownloadStatus(Base):
    """DownloadStatus model mapped to download_status table."""

    __tablename__ = "download_status"

    download_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    asin = Column(
        String(10), ForeignKey("books.asin", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    status = Column(String(20), default="pending", nullable=False, index=True)
    download_path = Column(String(1000), nullable=True)
    download_started_at = Column(DateTime(timezone=True), nullable=True)
    download_completed_at = Column(DateTime(timezone=True), nullable=True)
    attempt_number = Column(Integer, default=1)
    file_size_bytes = Column(BigInteger, nullable=True)
    download_format = Column(String(10), nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    # Relationships
    book = relationship("Book", back_populates="download_status", lazy="select")

    def __repr__(self) -> str:
        """Return a debug representation."""
        return f"<DownloadStatus(download_id={self.download_id}, asin={self.asin}, status={self.status})>"
