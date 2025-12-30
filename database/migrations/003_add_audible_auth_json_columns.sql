-- Migration: Add Audible auth.json storage columns
-- Description: Store parsed auth.json data in database instead of file paths
-- Date: 2025-12-21

-- Add new columns to users table for storing Audible auth.json data
ALTER TABLE users
ADD COLUMN audible_auth_json TEXT,
ADD COLUMN audible_email VARCHAR(255),
ADD COLUMN audible_device_name VARCHAR(255);

-- Create index on audible_email for quick lookups
CREATE INDEX idx_users_audible_email ON users(audible_email);

-- Create index on audible_device_name for filtering
CREATE INDEX idx_users_audible_device_name ON users(audible_device_name);

-- Add comment to explain the columns
COMMENT ON COLUMN users.audible_auth_json IS 'Parsed auth.json from audible-cli stored as JSON string. Contains access_token, refresh_token, device_info, customer_info, etc.';
COMMENT ON COLUMN users.audible_email IS 'User''s Audible account email extracted from auth.json for quick lookup';
COMMENT ON COLUMN users.audible_device_name IS 'Device name from Audible auth.json for display purposes';

-- Verify migration
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('audible_auth_json', 'audible_email', 'audible_device_name')
ORDER BY ordinal_position;
