"""Family model for SQLAlchemy ORM."""

from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.database.models.base import Base, get_current_timestamp

if TYPE_CHECKING:
    pass


class Family(Base):
    """Family model mapped to families table."""

    __tablename__ = "families"

    family_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    owner_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_current_timestamp, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_timestamp,
        onupdate=get_current_timestamp,
        nullable=False,
    )

    # Relationships
    owner = relationship("User", foreign_keys=[owner_user_id], lazy="select")
    members = relationship(
        "User",
        back_populates="family",
        foreign_keys="User.family_id",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Family(family_id={self.family_id}, name={self.name})>"
