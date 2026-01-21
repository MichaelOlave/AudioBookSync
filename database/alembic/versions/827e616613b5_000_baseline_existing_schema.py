"""000_baseline_existing_schema - Create core tables for Phase 1

Revision ID: 827e616613b5
Revises:
Create Date: 2026-01-20 22:40:12.563427

This migration creates the foundational tables for AudioBookSync:
- users: User accounts and authentication
- books: Audiobook metadata
- download_status: Download tracking
- decryption_status: Decryption tracking
- sync_history: Library sync audit trail
- error_log: Error logging
- genres: Book genres/categories
- book_genres: Many-to-many genre relationships
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '827e616613b5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create Phase 1 tables."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('auth_file_path', sa.String(500), nullable=True),
        sa.Column('activation_bytes', sa.String(16), nullable=True),
        sa.Column('audible_auth_json', sa.Text(), nullable=True),
        sa.Column('audible_email', sa.String(255), nullable=True),
        sa.Column('audible_device_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_sync_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('idx_users_audible_device_name', 'users', ['audible_device_name'])
    op.create_index('idx_users_audible_email', 'users', ['audible_email'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    op.create_index('idx_users_username', 'users', ['username'])

    # Create books table
    op.create_table(
        'books',
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('subtitle', sa.String(500), nullable=True),
        sa.Column('author', sa.String(500), nullable=True),
        sa.Column('narrator', sa.String(500), nullable=True),
        sa.Column('series_name', sa.String(300), nullable=True),
        sa.Column('series_sequence', sa.String(50), nullable=True),
        sa.Column('publisher', sa.String(200), nullable=True),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('language', sa.String(50), server_default='en-US', nullable=True),
        sa.Column('runtime_min', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('review_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('cover_art_url', sa.String(1000), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('is_downloaded', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_decrypted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('download_path', sa.String(1000), nullable=True),
        sa.Column('decrypted_path', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('asin'),
    )
    op.create_index('idx_books_author', 'books', ['author'])
    op.create_index('idx_books_is_decrypted', 'books', ['is_decrypted'])
    op.create_index('idx_books_is_downloaded', 'books', ['is_downloaded'])
    op.create_index('idx_books_purchase_date', 'books', ['purchase_date'])
    op.create_index('idx_books_series', 'books', ['series_name'])
    op.create_index('idx_books_title', 'books', ['title'])
    op.create_index('idx_books_user_id', 'books', ['user_id'])

    # Create download_status table
    op.create_table(
        'download_status',
        sa.Column('download_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('download_path', sa.String(1000), nullable=True),
        sa.Column('download_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('download_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('download_format', sa.String(10), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('download_id'),
    )
    op.create_index('idx_download_status_asin', 'download_status', ['asin'])
    op.create_index('idx_download_status_created_at', 'download_status', ['created_at'], desc=True)
    op.create_index('idx_download_status_status', 'download_status', ['status'])

    # Create decryption_status table
    op.create_table(
        'decryption_status',
        sa.Column('decryption_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('download_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('input_path', sa.String(1000), nullable=True),
        sa.Column('output_path', sa.String(1000), nullable=True),
        sa.Column('output_format', sa.String(10), server_default='m4b', nullable=True),
        sa.Column('decryption_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decryption_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['download_id'], ['download_status.download_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('decryption_id'),
    )
    op.create_index('idx_decryption_status_asin', 'decryption_status', ['asin'])
    op.create_index('idx_decryption_status_created_at', 'decryption_status', ['created_at'], desc=True)
    op.create_index('idx_decryption_status_status', 'decryption_status', ['status'])

    # Create sync_history table
    op.create_table(
        'sync_history',
        sa.Column('sync_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sync_type', sa.String(20), server_default='full', nullable=False),
        sa.Column('sync_started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('sync_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('books_found', sa.Integer(), server_default='0', nullable=True),
        sa.Column('books_added', sa.Integer(), server_default='0', nullable=True),
        sa.Column('books_removed', sa.Integer(), server_default='0', nullable=True),
        sa.Column('books_downloaded', sa.Integer(), server_default='0', nullable=True),
        sa.Column('books_decrypted', sa.Integer(), server_default='0', nullable=True),
        sa.Column('errors_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('status', sa.String(20), server_default='in_progress', nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('sync_id'),
    )
    op.create_index('idx_sync_history_started_at', 'sync_history', ['sync_started_at'], desc=True)
    op.create_index('idx_sync_history_status', 'sync_history', ['status'])
    op.create_index('idx_sync_history_user_id', 'sync_history', ['user_id'])

    # Create error_log table
    op.create_table(
        'error_log',
        sa.Column('error_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asin', sa.String(10), nullable=True),
        sa.Column('sync_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('error_type', sa.String(50), nullable=False),
        sa.Column('error_code', sa.String(20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(20), server_default='error', nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('resolved', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sync_id'], ['sync_history.sync_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('error_id'),
    )
    op.create_index('idx_error_log_asin', 'error_log', ['asin'])
    op.create_index('idx_error_log_error_type', 'error_log', ['error_type'])
    op.create_index('idx_error_log_resolved', 'error_log', ['resolved'])
    op.create_index('idx_error_log_severity', 'error_log', ['severity'])
    op.create_index('idx_error_log_timestamp', 'error_log', ['timestamp'], desc=True)
    op.create_index('idx_error_log_user_id', 'error_log', ['user_id'])

    # Create genres table
    op.create_table(
        'genres',
        sa.Column('genre_id', sa.Integer(), nullable=False),
        sa.Column('genre_name', sa.String(100), nullable=False),
        sa.Column('parent_genre_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['parent_genre_id'], ['genres.genre_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('genre_id'),
        sa.UniqueConstraint('genre_name'),
    )
    op.create_index('idx_genres_name', 'genres', ['genre_name'])
    op.create_index('idx_genres_parent', 'genres', ['parent_genre_id'])

    # Create book_genres table
    op.create_table(
        'book_genres',
        sa.Column('book_genre_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('asin', sa.String(10), nullable=False),
        sa.Column('genre_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asin'], ['books.asin'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['genre_id'], ['genres.genre_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('book_genre_id'),
        sa.UniqueConstraint('asin', 'genre_id'),
    )
    op.create_index('idx_book_genres_asin', 'book_genres', ['asin'])
    op.create_index('idx_book_genres_genre_id', 'book_genres', ['genre_id'])


def downgrade() -> None:
    """Downgrade schema - Drop all Phase 1 tables."""
    op.drop_index('idx_book_genres_genre_id', table_name='book_genres')
    op.drop_index('idx_book_genres_asin', table_name='book_genres')
    op.drop_table('book_genres')
    op.drop_index('idx_genres_parent', table_name='genres')
    op.drop_index('idx_genres_name', table_name='genres')
    op.drop_table('genres')
    op.drop_index('idx_error_log_user_id', table_name='error_log')
    op.drop_index('idx_error_log_timestamp', table_name='error_log')
    op.drop_index('idx_error_log_severity', table_name='error_log')
    op.drop_index('idx_error_log_resolved', table_name='error_log')
    op.drop_index('idx_error_log_error_type', table_name='error_log')
    op.drop_index('idx_error_log_asin', table_name='error_log')
    op.drop_table('error_log')
    op.drop_index('idx_sync_history_user_id', table_name='sync_history')
    op.drop_index('idx_sync_history_status', table_name='sync_history')
    op.drop_index('idx_sync_history_started_at', table_name='sync_history')
    op.drop_table('sync_history')
    op.drop_index('idx_decryption_status_status', table_name='decryption_status')
    op.drop_index('idx_decryption_status_created_at', table_name='decryption_status')
    op.drop_index('idx_decryption_status_asin', table_name='decryption_status')
    op.drop_table('decryption_status')
    op.drop_index('idx_download_status_status', table_name='download_status')
    op.drop_index('idx_download_status_created_at', table_name='download_status')
    op.drop_index('idx_download_status_asin', table_name='download_status')
    op.drop_table('download_status')
    op.drop_index('idx_books_user_id', table_name='books')
    op.drop_index('idx_books_title', table_name='books')
    op.drop_index('idx_books_series', table_name='books')
    op.drop_index('idx_books_purchase_date', table_name='books')
    op.drop_index('idx_books_is_downloaded', table_name='books')
    op.drop_index('idx_books_is_decrypted', table_name='books')
    op.drop_index('idx_books_author', table_name='books')
    op.drop_table('books')
    op.drop_index('idx_users_username', table_name='users')
    op.drop_index('idx_users_is_active', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_index('idx_users_audible_email', table_name='users')
    op.drop_index('idx_users_audible_device_name', table_name='users')
    op.drop_table('users')
