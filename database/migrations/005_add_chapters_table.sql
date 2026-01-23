-- Migration: Add chapters table for per-chapter metadata
-- Date: 2026-01-23
-- Purpose: Store normalized chapter metadata from Audible

BEGIN;

-- ============================================================================
-- CHAPTERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS chapters (
    chapter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asin VARCHAR(10) NOT NULL REFERENCES books(asin) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    title VARCHAR(500),
    start_offset_ms BIGINT,
    end_offset_ms BIGINT,
    length_ms BIGINT,
    raw_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, sequence_number)
);

CREATE INDEX IF NOT EXISTS idx_chapters_asin ON chapters(asin);
CREATE INDEX IF NOT EXISTS idx_chapters_asin_seq ON chapters(asin, sequence_number);

-- ============================================================================
-- TRIGGER: AUTO-UPDATE chapters.updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_chapters_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_chapters_updated_at ON chapters;
CREATE TRIGGER update_chapters_updated_at
BEFORE UPDATE ON chapters
FOR EACH ROW
EXECUTE FUNCTION update_chapters_timestamp();

COMMIT;
