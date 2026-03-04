-- Migration: Add password authentication support for API users
-- Date: 2024-12-20
-- Purpose: Enable OAuth2 password flow authentication for the FastAPI

BEGIN;

-- Add password_hash column to users table for API authentication
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- Create index for faster authentication lookups
CREATE INDEX IF NOT EXISTS idx_users_password_hash ON users(password_hash);

-- Add index on email for faster lookups during registration
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

COMMIT;

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================
-- The password_hash column stores bcrypt hashes of user passwords.
-- This enables:
-- - OAuth2 Password Flow authentication for the FastAPI
-- - Secure password verification without storing plaintext passwords
-- - Multi-user support with individual credentials
--
-- The hashes are created using passlib with bcrypt algorithm.
-- Cost factor: 12 rounds (default, suitable for production)
--
-- Existing users created via CLI/backend operations won't have passwords
-- initially. They can:
-- 1. Register through the API to create an account with password
-- 2. Be assigned passwords by administrators if needed
