"""001_add_metadata_tables - Add 7 metadata tables for Phase 3

Revision ID: c9e5c55eb233
Revises: 827e616613b5
Create Date: 2026-01-20 22:46:26.931829

This migration creates the metadata tables for audiobook information:
- contributors: Authors, narrators, editors
- book_contributors: Junction between books and contributors
- media_info: Audio technical details
- reading_progress: User listening progress
- book_availability: License and availability status
- companion_materials: PDFs, transcripts, etc.
- book_metadata_json: Flexible JSON metadata storage
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c9e5c55eb233'
down_revision: Union[str, Sequence[str], None] = '827e616613b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create Phase 3 metadata tables."""
    # Create contributors table
    op.create_table(
        'contributors',
        sa.Column('contributor_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('audible_asin', sa.String(10), nullable=True),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('contributor_id'),
        sa.UniqueConstraint('audible_asin'),
    )
    op.create_index('idx_contributors_audible_asin', 'contributors', ['audible_asin'])
    op.create_index('idx_contributors_name', 'contributors', ['name'])

    # Create book_contributors table
    op.create_table(
        'book_contributors',
        sa.Column('book_contributor_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('contributor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contributor_id'], ['contributors.contributor_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('book_contributor_id'),
        sa.UniqueConstraint('asin', 'contributor_id', 'role'),
    )
    op.create_index('idx_book_contributors_asin', 'book_contributors', ['asin'])
    op.create_index('idx_book_contributors_contributor_id', 'book_contributors', ['contributor_id'])

    # Create media_info table
    op.create_table(
        'media_info',
        sa.Column('media_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('codec', sa.String(50), nullable=True),
        sa.Column('bitrate', sa.Integer(), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=True),
        sa.Column('channels', sa.Integer(), nullable=True),
        sa.Column('format_type', sa.String(50), nullable=True),
        sa.Column('duration_ms', sa.BigInteger(), nullable=True),
        sa.Column('chapters_count', sa.Integer(), nullable=True),
        sa.Column('enhanced', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('media_id'),
        sa.UniqueConstraint('asin'),
    )
    op.create_index('idx_media_info_asin', 'media_info', ['asin'])

    # Create reading_progress table
    op.create_table(
        'reading_progress',
        sa.Column('progress_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('percent_complete', sa.Integer(), server_default='0', nullable=False),
        sa.Column('position_ms', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('is_finished', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('date_started', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_finished', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_position_update', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('progress_id'),
        sa.UniqueConstraint('asin', 'user_id'),
    )
    op.create_index('idx_reading_progress_asin', 'reading_progress', ['asin'])
    op.create_index('idx_reading_progress_is_finished', 'reading_progress', ['is_finished'])
    op.create_index('idx_reading_progress_user_id', 'reading_progress', ['user_id'])

    # Create book_availability table
    op.create_table(
        'book_availability',
        sa.Column('availability_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('is_playable', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_returnable', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_removable', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_downloadable', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('license_status', sa.String(50), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('availability_id'),
        sa.UniqueConstraint('asin'),
    )
    op.create_index('idx_book_availability_asin', 'book_availability', ['asin'])
    op.create_index('idx_book_availability_license_status', 'book_availability', ['license_status'])

    # Create companion_materials table
    op.create_table(
        'companion_materials',
        sa.Column('material_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('material_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('sequence_number', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('material_id'),
        sa.UniqueConstraint('asin', 'url'),
    )
    op.create_index('idx_companion_materials_asin', 'companion_materials', ['asin'])
    op.create_index('idx_companion_materials_type', 'companion_materials', ['material_type'])

    # Create book_metadata_json table
    op.create_table(
        'book_metadata_json',
        sa.Column('metadata_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('origin_asin', sa.String(10), nullable=True),
        sa.Column('brand', sa.String(100), nullable=True),
        sa.Column('periodical_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('relationships', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('badges', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('claim_code_url', sa.String(1000), nullable=True),
        sa.Column('parent_asin', sa.String(10), nullable=True),
        sa.Column('sku', sa.String(50), nullable=True),
        sa.Column('rating_distribution', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('custom_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('metadata_id'),
        sa.UniqueConstraint('asin'),
    )
    op.create_index('idx_book_metadata_asin', 'book_metadata_json', ['asin'])


def downgrade() -> None:
    """Downgrade schema - Drop all Phase 3 metadata tables."""
    op.drop_index('idx_book_metadata_asin', table_name='book_metadata_json')
    op.drop_table('book_metadata_json')
    op.drop_index('idx_companion_materials_type', table_name='companion_materials')
    op.drop_index('idx_companion_materials_asin', table_name='companion_materials')
    op.drop_table('companion_materials')
    op.drop_index('idx_book_availability_license_status', table_name='book_availability')
    op.drop_index('idx_book_availability_asin', table_name='book_availability')
    op.drop_table('book_availability')
    op.drop_index('idx_reading_progress_user_id', table_name='reading_progress')
    op.drop_index('idx_reading_progress_is_finished', table_name='reading_progress')
    op.drop_index('idx_reading_progress_asin', table_name='reading_progress')
    op.drop_table('reading_progress')
    op.drop_index('idx_media_info_asin', table_name='media_info')
    op.drop_table('media_info')
    op.drop_index('idx_book_contributors_contributor_id', table_name='book_contributors')
    op.drop_index('idx_book_contributors_asin', table_name='book_contributors')
    op.drop_table('book_contributors')
    op.drop_index('idx_contributors_name', table_name='contributors')
    op.drop_index('idx_contributors_audible_asin', table_name='contributors')
    op.drop_table('contributors')
