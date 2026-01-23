"""Chapter model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class Chapter(Base):
    """Chapter model mapped to chapters table."""

    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("asin", "sequence_number", name="uq_chapters_asin_seq"),)

    chapter_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    asin = Column(
        String(10),
        ForeignKey("books.asin", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number = Column(Integer, nullable=False, index=True)
    title = Column(String(500), nullable=True)
    start_offset_ms = Column(BigInteger, nullable=True)
    end_offset_ms = Column(BigInteger, nullable=True)
    length_ms = Column(BigInteger, nullable=True)
    raw_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    book = relationship("Book", back_populates="chapters", lazy="select")

    def __repr__(self) -> str:
        return f"<Chapter(chapter_id={self.chapter_id}, asin={self.asin}, seq={self.sequence_number})>"
