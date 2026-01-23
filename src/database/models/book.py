"""Book model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class Book(Base):
    """Book model mapped to books table."""

    __tablename__ = "books"

    asin = Column(String(10), primary_key=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500), nullable=True)
    author = Column(String(500), nullable=True)
    narrator = Column(String(500), nullable=True)
    series_name = Column(String(300), nullable=True, index=True)
    series_sequence = Column(String(50), nullable=True)
    publisher = Column(String(200), nullable=True)
    publication_date = Column(Date, nullable=True)
    purchase_date = Column(Date, nullable=True, index=True)
    description = Column(Text, nullable=True)
    language = Column(String(50), default="en-US")
    runtime_min = Column(Integer, nullable=True)
    rating = Column(Numeric(3, 2), nullable=True)
    review_count = Column(Integer, default=0)
    cover_art_url = Column(String(1000), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    checksum = Column(String(64), nullable=True)
    is_downloaded = Column(Boolean, default=False, nullable=False, index=True)
    is_decrypted = Column(Boolean, default=False, nullable=False, index=True)
    download_path = Column(String(1000), nullable=True)
    decrypted_path = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="books", lazy="select")
    download_status = relationship(
        "DownloadStatus",
        back_populates="book",
        cascade="all, delete-orphan",
        lazy="select",
    )
    decryption_status = relationship(
        "DecryptionStatus",
        back_populates="book",
        cascade="all, delete-orphan",
        lazy="select",
    )
    genres = relationship(
        "BookGenre",
        back_populates="book",
        cascade="all, delete-orphan",
        lazy="select",
    )
    chapters = relationship(
        "Chapter",
        back_populates="book",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Book(asin={self.asin}, title={self.title}, author={self.author})>"
