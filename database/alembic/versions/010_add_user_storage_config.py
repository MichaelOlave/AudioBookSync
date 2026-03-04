"""010_add_user_storage_config - Add storage provider configuration to users table

Revision ID: 010_add_user_storage_config
Revises: 009_add_user_books_table
Create Date: 2026-01-24 02:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "010_add_user_storage_config"
down_revision: Union[str, Sequence[str], None] = "009_add_user_books_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add storage_config column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "storage_config",
            postgresql.JSON(),
            nullable=True,
            comment="Storage provider configuration (provider_type, endpoint, credentials, etc)",
        ),
    )
    # Set default MinIO configuration for existing users
    op.execute(
        """
        UPDATE users
        SET storage_config = jsonb_build_object(
            'provider_type', 'minio',
            'endpoint', 'http://localhost:9000',
            'access_key', 'minioadmin',
            'secret_key', 'minioadmin',
            'use_ssl', false
        )
        WHERE storage_config IS NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema - Drop storage_config column from users table."""
    op.drop_column("users", "storage_config")
