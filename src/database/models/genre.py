"""Genre models for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    pass


class Genre(Base):
    """Genre model mapped to genres table."""

    __tablename__ = "genres"

    genre_id = Column(Integer, primary_key=True, autoincrement=True)
    genre_name = Column(String(100), unique=True, nullable=False, index=True)
    parent_genre_id = Column(
        Integer, ForeignKey("genres.genre_id", ondelete="SET NULL"), nullable=True, index=True
    )
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")

    # Self-referential relationship for hierarchical genres
    parent = relationship("Genre", remote_side=[genre_id], lazy="select")
    children = relationship("Genre", cascade="all, delete-orphan", lazy="select")

    def __repr__(self) -> str:
        return f"<Genre(genre_id={self.genre_id}, genre_name={self.genre_name})>"


class BookGenre(Base):
    """BookGenre model mapped to book_genres table (junction table)."""

    __tablename__ = "book_genres"

    book_genre_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    asin = Column(
        String(10), ForeignKey("books.asin", ondelete="CASCADE"), nullable=False, index=True
    )
    genre_id = Column(
        Integer, ForeignKey("genres.genre_id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")

    # Relationships
    book = relationship("Book", back_populates="genres", lazy="select")
    genre = relationship("Genre", lazy="select")

    def __repr__(self) -> str:
        return f"<BookGenre(book_genre_id={self.book_genre_id}, asin={self.asin}, genre_id={self.genre_id})>"
