"""Companion material model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, String, Text, Integer, BigInteger, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    from src.database.models.book import Book


class CompanionMaterial(Base):
    """CompanionMaterial model mapped to companion_materials table."""

    __tablename__ = "companion_materials"

    material_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    asin = Column(String(10), ForeignKey("books.asin", ondelete="CASCADE"), nullable=False, index=True)
    material_type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    url = Column(String(1000), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    sequence_number = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", nullable=False)

    def __repr__(self) -> str:
        return f"<CompanionMaterial(material_id={self.material_id}, asin={self.asin}, type={self.material_type})>"
