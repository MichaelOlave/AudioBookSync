"""004_add_application_logs_table - Create table for storing application logs in database

Revision ID: 004_add_application_logs
Revises: 003_encrypted_fallback
Create Date: 2026-01-22 12:00:00.000000

This migration creates the application_logs table for storing all application logs
in the database instead of file-based logs. Features:
- UUID primary key with auto-generation
- Indexed timestamp and level fields for fast querying
- Structured log data including module, function, line number
- Execution context (process_name, thread_id)
- JSON extra_data for structured metadata
- Exception details (type, message, stack trace)
- PostgreSQL trigger for automatic log retention based on log level
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '004_add_application_logs'
down_revision: Union[str, Sequence[str], None] = '003_encrypted_fallback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create application_logs table."""
    # Ensure uuid-ossp extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # Create application_logs table
    op.create_table(
        'application_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('module', sa.String(255), nullable=True),
        sa.Column('function', sa.String(255), nullable=True),
        sa.Column('line_number', sa.String(10), nullable=True),
        sa.Column('process_name', sa.String(255), nullable=True),
        sa.Column('thread_id', sa.String(50), nullable=True),
        sa.Column('extra_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('exception_type', sa.String(255), nullable=True),
        sa.Column('exception_message', sa.Text(), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('log_id')
    )

    # Create indexes for common query patterns
    op.create_index('idx_logs_timestamp', 'application_logs', ['timestamp'])
    op.create_index('idx_logs_level', 'application_logs', ['level'])
    op.create_index('idx_logs_timestamp_level', 'application_logs', ['timestamp', 'level'])
    op.create_index('idx_logs_module_level', 'application_logs', ['module', 'level'])
    op.create_index('idx_logs_process_timestamp', 'application_logs', ['process_name', 'timestamp'])


def downgrade() -> None:
    """Downgrade schema - Drop application_logs table."""
    # Drop indexes
    op.drop_index('idx_logs_process_timestamp', table_name='application_logs')
    op.drop_index('idx_logs_module_level', table_name='application_logs')
    op.drop_index('idx_logs_timestamp_level', table_name='application_logs')
    op.drop_index('idx_logs_level', table_name='application_logs')
    op.drop_index('idx_logs_timestamp', table_name='application_logs')

    # Drop table
    op.drop_table('application_logs')
