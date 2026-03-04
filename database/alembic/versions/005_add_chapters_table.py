"""005_add_chapters_table - Create chapters table for per-chapter metadata

Revision ID: 005_add_chapters_table
Revises: 004_add_application_logs
Create Date: 2026-01-23 12:00:00.000000

This migration adds a normalized chapters table to store chapter metadata
from Audible (titles, offsets, durations) with ordering per ASIN.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "005_add_chapters_table"
down_revision: Union[str, Sequence[str], None] = "004_add_application_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create chapters table."""
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table(
        "chapters",
        sa.Column(
            "chapter_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("asin", sa.String(10), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("start_offset_ms", sa.BigInteger(), nullable=True),
        sa.Column("end_offset_ms", sa.BigInteger(), nullable=True),
        sa.Column("length_ms", sa.BigInteger(), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["asin"], ["books.asin"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chapter_id"),
        sa.UniqueConstraint("asin", "sequence_number", name="uq_chapters_asin_seq"),
    )

    op.create_index("idx_chapters_asin", "chapters", ["asin"])
    op.create_index("idx_chapters_asin_seq", "chapters", ["asin", "sequence_number"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_chapters_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS update_chapters_updated_at ON chapters;
        CREATE TRIGGER update_chapters_updated_at
        BEFORE UPDATE ON chapters
        FOR EACH ROW
        EXECUTE FUNCTION update_chapters_timestamp();
        """
    )


def downgrade() -> None:
    """Downgrade schema - Drop chapters table."""
    op.execute("DROP TRIGGER IF EXISTS update_chapters_updated_at ON chapters;")
    op.execute("DROP FUNCTION IF EXISTS update_chapters_timestamp;")

    op.drop_index("idx_chapters_asin_seq", table_name="chapters")
    op.drop_index("idx_chapters_asin", table_name="chapters")
    op.drop_table("chapters")
