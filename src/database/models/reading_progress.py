"""Reading progress model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, String, Integer, Boolean, BigInteger, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    from src.database.models.book import Book
    from src.database.models.user import User


class ReadingProgress(Base):
    """ReadingProgress model mapped to reading_progress table."""

    __tablename__ = "reading_progress"

    progress_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    asin = Column(String(10), ForeignKey("books.asin", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    percent_complete = Column(Integer, default=0, nullable=False)
    position_ms = Column(BigInteger, default=0, nullable=False)
    is_finished = Column(Boolean, default=False, nullable=False, index=True)
    date_started = Column(DateTime(timezone=True), nullable=True)
    date_finished = Column(DateTime(timezone=True), nullable=True)
    last_position_update = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_current_timestamp, onupdate=get_current_timestamp, nullable=False)

    def __repr__(self) -> str:
        return f"<ReadingProgress(progress_id={self.progress_id}, asin={self.asin}, percent={self.percent_complete}%)>"
