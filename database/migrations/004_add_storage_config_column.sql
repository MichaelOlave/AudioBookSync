-- Migration: Add storage configuration column to users table
-- Version: 004
-- Description: Add JSONB column to store user's storage provider configuration

-- Add storage_config column to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS storage_config JSONB DEFAULT NULL;

-- Add comment for the new column
COMMENT ON COLUMN users.storage_config IS 'JSON configuration for storage provider (MinIO, S3, GCS, etc.)';

-- Create index on storage_config for better query performance if needed
CREATE INDEX IF NOT EXISTS idx_users_storage_config ON users USING GIN(storage_config);
