"""Book availability model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class BookAvailability(Base):
    """BookAvailability model mapped to book_availability table."""

    __tablename__ = "book_availability"

    availability_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    asin = Column(
        String(10),
        ForeignKey("books.asin", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    is_playable = Column(Boolean, default=True, nullable=False)
    is_returnable = Column(Boolean, default=True, nullable=False)
    is_removable = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    is_downloadable = Column(Boolean, default=True, nullable=False)
    license_status = Column(String(50), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return a debug representation."""
        return f"<BookAvailability(availability_id={self.availability_id}, asin={self.asin}, status={self.license_status})>"
