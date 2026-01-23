"""Application log model for SQLAlchemy ORM."""

from sqlalchemy import JSON, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.database.models.base import Base


class ApplicationLog(Base):
    """ApplicationLog model mapped to application_logs table."""

    __tablename__ = "application_logs"

    log_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="uuid_generate_v4()",
    )
    timestamp = Column(
        DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", nullable=False, index=True
    )
    level = Column(String(20), nullable=False, index=True)  # DEBUG/INFO/WARNING/ERROR/CRITICAL
    message = Column(Text, nullable=False)
    module = Column(String(255), nullable=True)
    function = Column(String(255), nullable=True)
    line_number = Column(String(10), nullable=True)
    process_name = Column(String(255), nullable=True)
    thread_id = Column(String(50), nullable=True)
    extra_data = Column(JSON, nullable=True)
    exception_type = Column(String(255), nullable=True)
    exception_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # Indexes for common query patterns
    __table_args__ = (
        Index("idx_logs_timestamp_level", "timestamp", "level"),
        Index("idx_logs_module_level", "module", "level"),
        Index("idx_logs_process_timestamp", "process_name", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<ApplicationLog(log_id={self.log_id}, level={self.level}, timestamp={self.timestamp})>"
