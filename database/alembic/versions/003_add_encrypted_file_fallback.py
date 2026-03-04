"""003_add_encrypted_file_fallback - Add encrypted file fallback storage for failed decryptions

Revision ID: 003_encrypted_fallback
Revises: 002_extend_metadata
Create Date: 2026-01-22 12:00:00.000000

This migration adds the encrypted_file_object_key column to decryption_status table
to support storing encrypted files in MinIO when decryption fails, allowing for
later retry attempts.

New Architecture:
- Downloads now use temporary directories instead of persistent DOWNLOAD_DIR
- Decryptions use temporary directories instead of persistent DECRYPTED_DIR
- On successful decryption: decrypted file uploaded to MinIO, encrypted file deleted
- On failed decryption: encrypted file uploaded to MinIO for retry, marked by encrypted_file_object_key
- Retries download encrypted file from MinIO, attempts decryption again
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_encrypted_fallback'
down_revision: Union[str, Sequence[str], None] = '002_extend_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add encrypted_file_object_key to decryption_status."""
    op.add_column('decryption_status',
        sa.Column('encrypted_file_object_key', sa.String(1000), nullable=True, index=True)
    )


def downgrade() -> None:
    """Downgrade schema - Remove encrypted_file_object_key from decryption_status."""
    op.drop_index('ix_decryption_status_encrypted_file_object_key', table_name='decryption_status')
    op.drop_column('decryption_status', 'encrypted_file_object_key')
