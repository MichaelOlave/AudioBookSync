"""Contributor models for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    from src.database.models.book import Book


class Contributor(Base):
    """Contributor model mapped to contributors table."""

    __tablename__ = "contributors"

    contributor_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    audible_asin = Column(String(10), unique=True, nullable=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_current_timestamp, onupdate=get_current_timestamp, nullable=False)

    # Relationships
    book_contributors = relationship(
        "BookContributor",
        back_populates="contributor",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Contributor(contributor_id={self.contributor_id}, name={self.name}, type={self.type})>"


class BookContributor(Base):
    """BookContributor model mapped to book_contributors table."""

    __tablename__ = "book_contributors"

    book_contributor_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    asin = Column(String(10), ForeignKey("books.asin", ondelete="CASCADE"), nullable=False, index=True)
    contributor_id = Column(UUID(as_uuid=True), ForeignKey("contributors.contributor_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    sequence_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", nullable=False)

    # Relationships
    contributor = relationship("Contributor", back_populates="book_contributors", lazy="select")

    def __repr__(self) -> str:
        return f"<BookContributor(book_contributor_id={self.book_contributor_id}, asin={self.asin}, role={self.role})>"
