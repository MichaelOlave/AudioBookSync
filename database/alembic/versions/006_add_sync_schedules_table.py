"""006_add_sync_schedules_table - Create sync_schedules table

Revision ID: 006_add_sync_schedules_table
Revises: 005_add_chapters_table
Create Date: 2026-01-23 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "006_add_sync_schedules_table"
down_revision: Union[str, Sequence[str], None] = "005_add_chapters_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create sync_schedules table."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "sync_schedules",
        sa.Column(
            "schedule_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=20), server_default="metadata_only", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("interval_minutes > 0", name="chk_sync_schedules_interval"),
        sa.CheckConstraint(
            "action IN ('metadata_only','download')",
            name="chk_sync_schedules_action",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("schedule_id"),
    )

    op.create_index("idx_sync_schedules_user_id", "sync_schedules", ["user_id"])
    op.create_index("idx_sync_schedules_enabled", "sync_schedules", ["enabled"])
    op.create_index("idx_sync_schedules_next_run_at", "sync_schedules", ["next_run_at"])


def downgrade() -> None:
    """Downgrade schema - Drop sync_schedules table."""
    op.drop_index("idx_sync_schedules_next_run_at", table_name="sync_schedules")
    op.drop_index("idx_sync_schedules_enabled", table_name="sync_schedules")
    op.drop_index("idx_sync_schedules_user_id", table_name="sync_schedules")
    op.drop_table("sync_schedules")
