"""Decryption status model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class DecryptionStatus(Base):
    """DecryptionStatus model mapped to decryption_status table."""

    __tablename__ = "decryption_status"

    decryption_id = Column(
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
    download_id = Column(
        UUID(as_uuid=True),
        ForeignKey("download_status.download_id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(20), default="pending", nullable=False, index=True)
    input_path = Column(String(1000), nullable=True)
    output_path = Column(String(1000), nullable=True)
    output_format = Column(String(10), default="m4b")
    decryption_started_at = Column(DateTime(timezone=True), nullable=True)
    decryption_completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    encrypted_file_object_key = Column(String(1000), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    # Relationships
    book = relationship("Book", back_populates="decryption_status", lazy="select")

    def __repr__(self) -> str:
        return f"<DecryptionStatus(decryption_id={self.decryption_id}, asin={self.asin}, status={self.status})>"
