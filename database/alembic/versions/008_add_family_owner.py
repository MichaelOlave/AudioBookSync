"""008_add_family_owner - Add family owner (head) reference

Revision ID: 008_add_family_owner
Revises: 007_add_family_table
Create Date: 2026-01-24 01:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "008_add_family_owner"
down_revision: Union[str, Sequence[str], None] = "007_add_family_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add owner_user_id to families."""
    op.add_column(
        "families",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        """
        UPDATE families AS f
        SET owner_user_id = sub.user_id
        FROM (
            SELECT DISTINCT ON (family_id) family_id, user_id
            FROM users
            WHERE family_id IS NOT NULL
            ORDER BY family_id, created_at
        ) AS sub
        WHERE f.family_id = sub.family_id
        """
    )

    op.create_foreign_key(
        "fk_families_owner_user_id",
        "families",
        "users",
        ["owner_user_id"],
        ["user_id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_families_owner_user_id", "families", ["owner_user_id"])


def downgrade() -> None:
    """Downgrade schema - Drop owner_user_id from families."""
    op.drop_index("idx_families_owner_user_id", table_name="families")
    op.drop_constraint("fk_families_owner_user_id", "families", type_="foreignkey")
    op.drop_column("families", "owner_user_id")
