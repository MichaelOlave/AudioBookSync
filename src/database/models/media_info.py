"""Media info model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class MediaInfo(Base):
    """MediaInfo model mapped to media_info table."""

    __tablename__ = "media_info"

    media_id = Column(
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
    codec = Column(String(50), nullable=True)
    bitrate = Column(Integer, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    format_type = Column(String(50), nullable=True)
    duration_ms = Column(BigInteger, nullable=True)
    chapters_count = Column(Integer, nullable=True)
    enhanced = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MediaInfo(media_id={self.media_id}, asin={self.asin}, codec={self.codec})>"
