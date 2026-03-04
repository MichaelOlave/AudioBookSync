"""009_add_user_books_table - Add per-user book ownership and status fields

Revision ID: 009_add_user_books_table
Revises: 008_add_family_owner
Create Date: 2026-01-24 01:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "009_add_user_books_table"
down_revision: Union[str, Sequence[str], None] = "008_add_family_owner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add user_books table and user_id to status tables."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "user_books",
        sa.Column(
            "user_book_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asin", sa.String(length=10), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("is_downloaded", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_decrypted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("download_path", sa.String(length=1000), nullable=True),
        sa.Column("decrypted_path", sa.String(length=1000), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asin"], ["books.asin"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_book_id"),
        sa.UniqueConstraint("user_id", "asin", name="uq_user_books_user_asin"),
    )

    op.create_index("idx_user_books_user_id", "user_books", ["user_id"])
    op.create_index("idx_user_books_asin", "user_books", ["asin"])
    op.create_index("idx_user_books_is_downloaded", "user_books", ["is_downloaded"])
    op.create_index("idx_user_books_is_decrypted", "user_books", ["is_decrypted"])

    op.execute(
        """
        INSERT INTO user_books (
            user_book_id,
            user_id,
            asin,
            purchase_date,
            is_downloaded,
            is_decrypted,
            download_path,
            decrypted_path,
            file_size_bytes,
            checksum,
            created_at,
            updated_at
        )
        SELECT
            uuid_generate_v4(),
            user_id,
            asin,
            purchase_date,
            is_downloaded,
            is_decrypted,
            download_path,
            decrypted_path,
            file_size_bytes,
            checksum,
            created_at,
            updated_at
        FROM books
        WHERE user_id IS NOT NULL
        ON CONFLICT (user_id, asin) DO NOTHING
        """
    )

    op.add_column(
        "download_status",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "decryption_status",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        """
        UPDATE download_status ds
        SET user_id = b.user_id
        FROM books b
        WHERE ds.asin = b.asin
          AND b.user_id IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE decryption_status ds
        SET user_id = d.user_id
        FROM download_status d
        WHERE ds.download_id = d.download_id
          AND d.user_id IS NOT NULL
        """
    )

    op.execute(
        """
        UPDATE decryption_status ds
        SET user_id = b.user_id
        FROM books b
        WHERE ds.user_id IS NULL
          AND ds.asin = b.asin
          AND b.user_id IS NOT NULL
        """
    )

    op.create_foreign_key(
        "fk_download_status_user_id",
        "download_status",
        "users",
        ["user_id"],
        ["user_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_decryption_status_user_id",
        "decryption_status",
        "users",
        ["user_id"],
        ["user_id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_download_status_user_id", "download_status", ["user_id"])
    op.create_index("idx_decryption_status_user_id", "decryption_status", ["user_id"])


def downgrade() -> None:
    """Downgrade schema - Drop user_books table and status user_id fields."""
    op.drop_index("idx_decryption_status_user_id", table_name="decryption_status")
    op.drop_index("idx_download_status_user_id", table_name="download_status")
    op.drop_constraint("fk_decryption_status_user_id", "decryption_status", type_="foreignkey")
    op.drop_constraint("fk_download_status_user_id", "download_status", type_="foreignkey")
    op.drop_column("decryption_status", "user_id")
    op.drop_column("download_status", "user_id")

    op.drop_index("idx_user_books_is_decrypted", table_name="user_books")
    op.drop_index("idx_user_books_is_downloaded", table_name="user_books")
    op.drop_index("idx_user_books_asin", table_name="user_books")
    op.drop_index("idx_user_books_user_id", table_name="user_books")
    op.drop_table("user_books")
