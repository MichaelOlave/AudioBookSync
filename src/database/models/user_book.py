"""UserBook model for per-user library ownership."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class UserBook(Base):
    """UserBook model mapped to user_books table."""

    __tablename__ = "user_books"

    user_book_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asin = Column(
        String(10),
        ForeignKey("books.asin", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    purchase_date = Column(Date, nullable=True)
    is_downloaded = Column(Boolean, default=False, nullable=False, index=True)
    is_decrypted = Column(Boolean, default=False, nullable=False, index=True)
    download_path = Column(String(1000), nullable=True)
    decrypted_path = Column(String(1000), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    # Relationships
    book = relationship("Book", back_populates="user_books", lazy="select")
    user = relationship("User", back_populates="user_books", lazy="select")

    def __repr__(self) -> str:
        """Return a debug representation."""
        return f"<UserBook(user_book_id={self.user_book_id}, user_id={self.user_id}, asin={self.asin})>"
