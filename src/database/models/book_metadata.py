"""Book metadata JSON model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
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
    # Core metadata
    title = Column(String(500), nullable=True)
    subtitle = Column(String(500), nullable=True)
    language = Column(String(50), nullable=True)
    publisher_name = Column(String(255), nullable=True)
    format_type = Column(String(50), nullable=True)
    content_type = Column(String(50), nullable=True)
    content_delivery_type = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)

    # Dates
    publication_datetime = Column(DateTime(timezone=True), nullable=True)
    release_date = Column(DateTime(timezone=True), nullable=True)
    issue_date = Column(DateTime(timezone=True), nullable=True)
    purchase_date = Column(DateTime(timezone=True), nullable=True)

    # Audio properties
    runtime_length_min = Column(Integer, nullable=True)

    # Flags
    is_listenable = Column(Boolean, nullable=True)
    is_purchasability_suppressed = Column(Boolean, nullable=True)
    is_adult_product = Column(Boolean, nullable=True)
    has_children = Column(Boolean, nullable=True)

    # Identifiers
    origin_asin = Column(String(10), nullable=True)
    sku = Column(String(50), nullable=True)
    isbn = Column(String(50), nullable=True)
    parent_asin = Column(String(10), nullable=True)
    brand = Column(String(100), nullable=True)

    # Complex nested structures (JSON)
    authors = Column(JSON, nullable=True)  # Array of {asin, name}
    narrators = Column(JSON, nullable=True)  # Array of {asin, name}
    rating = Column(JSON, nullable=True)  # Detailed rating distribution
    product_images = Column(JSON, nullable=True)  # Image URLs by size
    social_media_images = Column(JSON, nullable=True)  # Social images
    available_codecs = Column(JSON, nullable=True)  # Audio codec options
    library_status = Column(JSON, nullable=True)  # User's library status
    thesaurus_subject_keywords = Column(JSON, nullable=True)  # Subject keywords

    # Legacy/flexible fields
    periodical_info = Column(JSON, nullable=True)
    relationships = Column(JSON, nullable=True)
    badges = Column(JSON, nullable=True)
    claim_code_url = Column(String(1000), nullable=True)
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
        return f"<BookMetadataJson(metadata_id={self.metadata_id}, asin={self.asin}, title={self.title})>"
