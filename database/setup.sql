-- =====================================================
-- AudioBookSync Database Setup Script
-- =====================================================
-- This script creates the database and sets up initial configuration
-- Run this before running schema.sql
-- =====================================================

-- Create the database (run as postgres superuser)
-- Note: You may need to run this command separately from psql command line
-- CREATE DATABASE audiobooksync;

-- Connect to the database
\c audiobooksync

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS public;

-- Grant privileges
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Display confirmation
SELECT 'Database audiobooksync is ready for schema installation' AS status;

-- Next step: Run schema.sql
-- \i schema.sql
