"""007_add_family_table - Create families table and user sharing fields

Revision ID: 007_add_family_table
Revises: 006_add_sync_schedules_table
Create Date: 2026-01-24 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "007_add_family_table"
down_revision: Union[str, Sequence[str], None] = "006_add_sync_schedules_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create families table and user sharing fields."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "families",
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=True),
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
        sa.PrimaryKeyConstraint("family_id"),
    )

    op.add_column(
        "users",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "share_library_with_family",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_users_family_id",
        "users",
        "families",
        ["family_id"],
        ["family_id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_users_family_id", "users", ["family_id"])


def downgrade() -> None:
    """Downgrade schema - Drop families table and user sharing fields."""
    op.drop_index("idx_users_family_id", table_name="users")
    op.drop_constraint("fk_users_family_id", "users", type_="foreignkey")
    op.drop_column("users", "share_library_with_family")
    op.drop_column("users", "family_id")
    op.drop_table("families")
