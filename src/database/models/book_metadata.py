"""Book metadata JSON model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class BookMetadataJson(Base):
    """BookMetadataJson model mapped to book_metadata_json table."""

    __tablename__ = "book_metadata_json"

    metadata_id = Column(
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
    origin_asin = Column(String(10), nullable=True)
    brand = Column(String(100), nullable=True)
    periodical_info = Column(JSON, nullable=True)
    relationships = Column(JSON, nullable=True)
    badges = Column(JSON, nullable=True)
    claim_code_url = Column(String(1000), nullable=True)
    parent_asin = Column(String(10), nullable=True)
    sku = Column(String(50), nullable=True)
    rating_distribution = Column(JSON, nullable=True)
    custom_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<BookMetadataJson(metadata_id={self.metadata_id}, asin={self.asin}, brand={self.brand})>"
