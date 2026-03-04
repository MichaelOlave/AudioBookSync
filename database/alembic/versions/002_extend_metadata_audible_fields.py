"""002_extend_metadata_audible_fields - Add Audible metadata fields to book_metadata_json

Revision ID: 002_extend_metadata
Revises: c9e5c55eb233
Create Date: 2026-01-21 12:00:00.000000

This migration extends the book_metadata_json table with additional fields from Audible API
to support comprehensive audiobook metadata storage:
- Core metadata: title, subtitle, language, publisher, format, status
- Date fields: publication_datetime, release_date, issue_date, purchase_date
- Audio properties: runtime_length_min
- Boolean flags: is_listenable, is_purchasability_suppressed, is_adult_product, has_children
- Identifiers: isbn
- Complex structures (JSON): authors, narrators, rating, images, codecs, library_status, keywords
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_extend_metadata'
down_revision: Union[str, Sequence[str], None] = 'c9e5c55eb233'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add new Audible metadata columns to book_metadata_json."""
    # Core metadata columns
    op.add_column('book_metadata_json',
        sa.Column('title', sa.String(500), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('subtitle', sa.String(500), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('language', sa.String(50), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('publisher_name', sa.String(255), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('format_type', sa.String(50), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('content_type', sa.String(50), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('content_delivery_type', sa.String(50), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('status', sa.String(50), nullable=True)
    )

    # Date columns
    op.add_column('book_metadata_json',
        sa.Column('publication_datetime', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('release_date', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('issue_date', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('purchase_date', sa.DateTime(timezone=True), nullable=True)
    )

    # Audio properties
    op.add_column('book_metadata_json',
        sa.Column('runtime_length_min', sa.Integer(), nullable=True)
    )

    # Boolean flags
    op.add_column('book_metadata_json',
        sa.Column('is_listenable', sa.Boolean(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('is_purchasability_suppressed', sa.Boolean(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('is_adult_product', sa.Boolean(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('has_children', sa.Boolean(), nullable=True)
    )

    # Additional identifier
    op.add_column('book_metadata_json',
        sa.Column('isbn', sa.String(50), nullable=True)
    )

    # Complex structures (JSON)
    op.add_column('book_metadata_json',
        sa.Column('authors', sa.JSON(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('narrators', sa.JSON(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('rating', sa.JSON(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('product_images', sa.JSON(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('social_media_images', sa.JSON(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('available_codecs', sa.JSON(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('library_status', sa.JSON(), nullable=True)
    )
    op.add_column('book_metadata_json',
        sa.Column('thesaurus_subject_keywords', sa.JSON(), nullable=True)
    )

    # Create indexes for frequently queried columns
    op.create_index('idx_book_metadata_title', 'book_metadata_json', ['title'])
    op.create_index('idx_book_metadata_language', 'book_metadata_json', ['language'])
    op.create_index('idx_book_metadata_status', 'book_metadata_json', ['status'])
    op.create_index('idx_book_metadata_is_listenable', 'book_metadata_json', ['is_listenable'])


def downgrade() -> None:
    """Downgrade schema - Remove added Audible metadata columns."""
    # Drop indexes
    op.drop_index('idx_book_metadata_is_listenable', table_name='book_metadata_json')
    op.drop_index('idx_book_metadata_status', table_name='book_metadata_json')
    op.drop_index('idx_book_metadata_language', table_name='book_metadata_json')
    op.drop_index('idx_book_metadata_title', table_name='book_metadata_json')

    # Drop columns
    op.drop_column('book_metadata_json', 'thesaurus_subject_keywords')
    op.drop_column('book_metadata_json', 'library_status')
    op.drop_column('book_metadata_json', 'available_codecs')
    op.drop_column('book_metadata_json', 'social_media_images')
    op.drop_column('book_metadata_json', 'product_images')
    op.drop_column('book_metadata_json', 'rating')
    op.drop_column('book_metadata_json', 'narrators')
    op.drop_column('book_metadata_json', 'authors')
    op.drop_column('book_metadata_json', 'isbn')
    op.drop_column('book_metadata_json', 'has_children')
    op.drop_column('book_metadata_json', 'is_adult_product')
    op.drop_column('book_metadata_json', 'is_purchasability_suppressed')
    op.drop_column('book_metadata_json', 'is_listenable')
    op.drop_column('book_metadata_json', 'runtime_length_min')
    op.drop_column('book_metadata_json', 'purchase_date')
    op.drop_column('book_metadata_json', 'issue_date')
    op.drop_column('book_metadata_json', 'release_date')
    op.drop_column('book_metadata_json', 'publication_datetime')
    op.drop_column('book_metadata_json', 'content_delivery_type')
    op.drop_column('book_metadata_json', 'content_type')
    op.drop_column('book_metadata_json', 'format_type')
    op.drop_column('book_metadata_json', 'publisher_name')
    op.drop_column('book_metadata_json', 'language')
    op.drop_column('book_metadata_json', 'subtitle')
    op.drop_column('book_metadata_json', 'title')
