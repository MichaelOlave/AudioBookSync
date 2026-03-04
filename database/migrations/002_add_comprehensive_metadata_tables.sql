-- Migration: Add comprehensive metadata tables for Audible data
-- Date: 2024-12-20
-- Purpose: Support rich metadata from Audible API including contributors,
--          media info, reading progress, and availability status

BEGIN;

-- ============================================================================
-- 1. CONTRIBUTORS TABLE
-- ============================================================================
-- Stores information about book contributors (authors, narrators, editors, etc.)
CREATE TABLE IF NOT EXISTS contributors (
    contributor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audible_asin VARCHAR(10) UNIQUE,  -- Audible's ASIN for the contributor
    name VARCHAR(500) NOT NULL,
    type VARCHAR(50),  -- "author", "narrator", "editor", "translator", etc.
    description TEXT,
    url VARCHAR(1000),  -- URL to Audible profile if available
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contributors_name ON contributors(name);
CREATE INDEX IF NOT EXISTS idx_contributors_audible_asin ON contributors(audible_asin);

-- ============================================================================
-- 2. BOOK_CONTRIBUTORS JUNCTION TABLE
-- ============================================================================
-- Links books to their contributors with role information
CREATE TABLE IF NOT EXISTS book_contributors (
    book_contributor_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin VARCHAR(10) NOT NULL REFERENCES books(asin) ON DELETE CASCADE,
    contributor_id UUID NOT NULL REFERENCES contributors(contributor_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- "author", "narrator", "editor", "translator", etc.
    sequence_number INTEGER,  -- Order of display (1st author, 2nd author, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, contributor_id, role)  -- Prevent duplicate role assignments
);

CREATE INDEX IF NOT EXISTS idx_book_contributors_asin ON book_contributors(asin);
CREATE INDEX IF NOT EXISTS idx_book_contributors_contributor_id ON book_contributors(contributor_id);

-- ============================================================================
-- 3. MEDIA_INFO TABLE
-- ============================================================================
-- Stores technical audio information
CREATE TABLE IF NOT EXISTS media_info (
    media_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin VARCHAR(10) NOT NULL UNIQUE REFERENCES books(asin) ON DELETE CASCADE,
    codec VARCHAR(50),  -- AAC, MP3, FLAC, OGG, etc.
    bitrate INTEGER,  -- bits per second
    sample_rate INTEGER,  -- Hz (e.g., 44100, 48000)
    channels INTEGER,  -- 1 (mono), 2 (stereo), 6 (5.1), etc.
    format_type VARCHAR(50),  -- audiobook, podcast, performance, etc.
    duration_ms BIGINT,  -- Total duration in milliseconds
    chapters_count INTEGER,  -- Number of chapters if available
    enhanced BOOLEAN DEFAULT false,  -- Audible Enhanced Audio (PDF, images, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_media_info_asin ON media_info(asin);

-- ============================================================================
-- 4. READING_PROGRESS TABLE
-- ============================================================================
-- Tracks user's listening progress per book
CREATE TABLE IF NOT EXISTS reading_progress (
    progress_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin VARCHAR(10) NOT NULL REFERENCES books(asin) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    percent_complete INTEGER DEFAULT 0 CHECK (percent_complete >= 0 AND percent_complete <= 100),
    position_ms BIGINT DEFAULT 0,  -- Last listening position in milliseconds
    is_finished BOOLEAN DEFAULT false,
    date_started TIMESTAMP WITH TIME ZONE,
    date_finished TIMESTAMP WITH TIME ZONE,
    last_position_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, user_id)  -- One progress record per user per book
);

CREATE INDEX IF NOT EXISTS idx_reading_progress_user_id ON reading_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_reading_progress_asin ON reading_progress(asin);
CREATE INDEX IF NOT EXISTS idx_reading_progress_is_finished ON reading_progress(is_finished);

-- ============================================================================
-- 5. BOOK_AVAILABILITY TABLE
-- ============================================================================
-- Tracks user's availability and rights for each book
CREATE TABLE IF NOT EXISTS book_availability (
    availability_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin VARCHAR(10) NOT NULL UNIQUE REFERENCES books(asin) ON DELETE CASCADE,
    is_playable BOOLEAN DEFAULT true,  -- Can the user currently play this?
    is_returnable BOOLEAN DEFAULT true,  -- Can be returned to Audible?
    is_removable BOOLEAN DEFAULT true,  -- Can be removed from library?
    is_archived BOOLEAN DEFAULT false,  -- Is it archived?
    is_downloadable BOOLEAN DEFAULT true,  -- Can be downloaded?
    license_status VARCHAR(50),  -- active, expired, revoked, etc.
    expires_at TIMESTAMP WITH TIME ZONE,  -- License expiration date if applicable
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_book_availability_asin ON book_availability(asin);
CREATE INDEX IF NOT EXISTS idx_book_availability_license_status ON book_availability(license_status);

-- ============================================================================
-- 6. COMPANION_MATERIALS TABLE
-- ============================================================================
-- Tracks supplementary materials (PDFs, images, transcripts, etc.)
CREATE TABLE IF NOT EXISTS companion_materials (
    material_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin VARCHAR(10) NOT NULL REFERENCES books(asin) ON DELETE CASCADE,
    material_type VARCHAR(50) NOT NULL,  -- "pdf", "image", "transcript", "supplemental", etc.
    title VARCHAR(500),
    url VARCHAR(1000) NOT NULL,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),  -- application/pdf, image/jpeg, etc.
    sequence_number INTEGER,  -- Order of display
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asin, url)  -- Prevent duplicate URLs
);

CREATE INDEX IF NOT EXISTS idx_companion_materials_asin ON companion_materials(asin);
CREATE INDEX IF NOT EXISTS idx_companion_materials_type ON companion_materials(material_type);

-- ============================================================================
-- 7. BOOK_METADATA_JSON TABLE
-- ============================================================================
-- Flexible storage for additional metadata that doesn't fit structured tables
CREATE TABLE IF NOT EXISTS book_metadata_json (
    metadata_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asin VARCHAR(10) NOT NULL UNIQUE REFERENCES books(asin) ON DELETE CASCADE,
    origin_asin VARCHAR(10),  -- If this is a re-published version, original ASIN
    brand VARCHAR(100),  -- Audible brand/imprint
    periodical_info JSONB,  -- If it's a periodical: issue_number, issue_date, etc.
    relationships JSONB,  -- Related products, sequels, series info, etc.
    badges JSONB,  -- Content badges: [{"name": "Audible Exclusive", ...}]
    claim_code_url VARCHAR(1000),  -- Claim code if provided
    parent_asin VARCHAR(10),  -- Parent product if this is a child
    sku VARCHAR(50),  -- Stock keeping unit
    rating_distribution JSONB,  -- Distribution of ratings: {"5": 100, "4": 45, ...}
    custom_metadata JSONB,  -- Any additional metadata from API
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_book_metadata_asin ON book_metadata_json(asin);

-- ============================================================================
-- 8. UPDATE EXISTING BOOKS TABLE
-- ============================================================================
-- Add new columns to books table for common metadata
ALTER TABLE books
ADD COLUMN IF NOT EXISTS is_finished BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS date_first_heard TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS origin_asin VARCHAR(10),
ADD COLUMN IF NOT EXISTS brand VARCHAR(100),
ADD COLUMN IF NOT EXISTS metadata_json JSONB;  -- Fallback for other metadata

-- ============================================================================
-- 9. UPDATE GENRES TABLE FOR BETTER CATEGORIZATION
-- ============================================================================
-- Enhance genres table to support Audible's richer category structure
ALTER TABLE genres
ADD COLUMN IF NOT EXISTS audible_category_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS category_type VARCHAR(50),  -- "genre", "category", "browse_node", etc.
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS popularity_rank INTEGER;

CREATE INDEX IF NOT EXISTS idx_genres_audible_category_id ON genres(audible_category_id);

-- ============================================================================
-- 10. CREATE VIEW: v_books_with_metadata
-- ============================================================================
-- Comprehensive view combining books with all related metadata
CREATE OR REPLACE VIEW v_books_with_metadata AS
SELECT
    b.*,
    -- Contributors (aggregated)
    json_agg(json_build_object(
        'contributor_id', c.contributor_id,
        'name', c.name,
        'role', bc.role,
        'type', c.type
    )) FILTER (WHERE bc.book_contributor_id IS NOT NULL) AS contributors,
    -- Media info
    m.codec,
    m.bitrate,
    m.sample_rate,
    m.channels,
    m.format_type,
    m.duration_ms,
    m.chapters_count,
    m.enhanced,
    -- Reading progress
    rp.percent_complete,
    rp.position_ms,
    rp.is_finished AS user_finished,
    rp.date_started,
    rp.date_finished,
    -- Availability
    ba.is_playable,
    ba.is_returnable,
    ba.is_removable,
    ba.is_archived,
    ba.is_downloadable,
    ba.license_status,
    ba.expires_at,
    -- Companion materials (aggregated)
    json_agg(json_build_object(
        'material_id', cm.material_id,
        'material_type', cm.material_type,
        'title', cm.title,
        'url', cm.url
    )) FILTER (WHERE cm.material_id IS NOT NULL) AS companion_materials,
    -- Additional metadata (from book_metadata_json table)
    bmj.periodical_info,
    bmj.relationships,
    bmj.badges,
    bmj.claim_code_url,
    bmj.rating_distribution
FROM books b
LEFT JOIN book_contributors bc ON b.asin = bc.asin
LEFT JOIN contributors c ON bc.contributor_id = c.contributor_id
LEFT JOIN media_info m ON b.asin = m.asin
LEFT JOIN reading_progress rp ON b.asin = rp.asin
LEFT JOIN book_availability ba ON b.asin = ba.asin
LEFT JOIN companion_materials cm ON b.asin = cm.asin
LEFT JOIN book_metadata_json bmj ON b.asin = bmj.asin
GROUP BY b.asin, b.user_id, b.title, b.subtitle, b.author, b.narrator,
         b.series_name, b.series_sequence, b.publisher, b.publication_date,
         b.purchase_date, b.description, b.language, b.runtime_min,
         b.rating, b.review_count, b.cover_art_url, b.file_size_bytes,
         b.checksum, b.is_downloaded, b.is_decrypted, b.download_path,
         b.decrypted_path, b.created_at, b.updated_at, b.is_finished,
         b.date_first_heard, b.origin_asin, b.brand, b.metadata_json,
         m.media_id, m.codec, m.bitrate, m.sample_rate, m.channels, m.format_type,
         m.duration_ms, m.chapters_count, m.enhanced,
         rp.progress_id, rp.percent_complete, rp.position_ms, rp.is_finished, rp.date_started, rp.date_finished,
         ba.availability_id, ba.is_playable, ba.is_returnable, ba.is_removable, ba.is_archived,
         ba.is_downloadable, ba.license_status, ba.expires_at,
         bmj.metadata_id, bmj.periodical_info, bmj.relationships,
         bmj.badges, bmj.claim_code_url, bmj.rating_distribution;

-- ============================================================================
-- 11. CREATE VIEW: v_reading_statistics
-- ============================================================================
-- User's reading statistics
CREATE OR REPLACE VIEW v_reading_statistics AS
SELECT
    u.user_id,
    u.username,
    COUNT(DISTINCT b.asin) AS total_books,
    COUNT(DISTINCT CASE WHEN rp.is_finished THEN b.asin END) AS finished_books,
    COUNT(DISTINCT CASE WHEN rp.percent_complete > 0 AND rp.percent_complete < 100 THEN b.asin END) AS in_progress_books,
    COUNT(DISTINCT CASE WHEN rp.percent_complete = 0 THEN b.asin END) AS unstarted_books,
    ROUND(AVG(rp.percent_complete)::numeric, 2) AS avg_progress_percent,
    MAX(rp.last_position_update) AS last_listened
FROM users u
LEFT JOIN books b ON u.user_id = b.user_id
LEFT JOIN reading_progress rp ON b.asin = rp.asin AND u.user_id = rp.user_id
GROUP BY u.user_id, u.username;

-- ============================================================================
-- 12. CREATE TRIGGERS FOR AUTO-UPDATE
-- ============================================================================

-- Trigger to auto-update reading_progress.updated_at
CREATE OR REPLACE FUNCTION update_reading_progress_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_reading_progress_updated_at ON reading_progress;
CREATE TRIGGER update_reading_progress_updated_at
BEFORE UPDATE ON reading_progress
FOR EACH ROW
EXECUTE FUNCTION update_reading_progress_timestamp();

-- Trigger to auto-update media_info.updated_at
CREATE OR REPLACE FUNCTION update_media_info_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_media_info_updated_at ON media_info;
CREATE TRIGGER update_media_info_updated_at
BEFORE UPDATE ON media_info
FOR EACH ROW
EXECUTE FUNCTION update_media_info_timestamp();

-- Trigger to auto-update book_availability.updated_at
CREATE OR REPLACE FUNCTION update_book_availability_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_book_availability_updated_at ON book_availability;
CREATE TRIGGER update_book_availability_updated_at
BEFORE UPDATE ON book_availability
FOR EACH ROW
EXECUTE FUNCTION update_book_availability_timestamp();

-- Trigger to auto-update contributors.updated_at
CREATE OR REPLACE FUNCTION update_contributors_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_contributors_updated_at ON contributors;
CREATE TRIGGER update_contributors_updated_at
BEFORE UPDATE ON contributors
FOR EACH ROW
EXECUTE FUNCTION update_contributors_timestamp();

-- Trigger to auto-update book_metadata_json.updated_at
CREATE OR REPLACE FUNCTION update_book_metadata_json_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_book_metadata_json_updated_at ON book_metadata_json;
CREATE TRIGGER update_book_metadata_json_updated_at
BEFORE UPDATE ON book_metadata_json
FOR EACH ROW
EXECUTE FUNCTION update_book_metadata_json_timestamp();

-- ============================================================================
-- 13. INSERT INITIAL DATA FOR BOOK_AVAILABILITY ON NEW BOOKS
-- ============================================================================
-- Create trigger to auto-create availability record when book is inserted
CREATE OR REPLACE FUNCTION create_book_availability_on_insert()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO book_availability (asin, is_playable, is_returnable, is_removable, is_downloadable)
    VALUES (NEW.asin, true, true, true, true)
    ON CONFLICT (asin) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS create_book_availability ON books;
CREATE TRIGGER create_book_availability
AFTER INSERT ON books
FOR EACH ROW
EXECUTE FUNCTION create_book_availability_on_insert();

-- ============================================================================
-- COMMIT TRANSACTION
-- ============================================================================
COMMIT;

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================
-- This migration adds comprehensive metadata support for Audible data:
--
-- NEW TABLES:
-- - contributors: Author, narrator, and other contributor information
-- - book_contributors: Junction table linking books to contributors with roles
-- - media_info: Technical audio information (codec, bitrate, sample rate, etc.)
-- - reading_progress: User's listening progress per book
-- - book_availability: User's availability and rights for each book
-- - companion_materials: PDFs, images, transcripts, and other supplementary materials
-- - book_metadata_json: Flexible JSON storage for additional metadata
--
-- VIEWS:
-- - v_books_with_metadata: Comprehensive view combining all book data
-- - v_reading_statistics: User reading statistics and progress summary
--
-- This design allows storing rich Audible metadata while maintaining:
-- - Normalized structure for efficient queries
-- - Flexible JSONB columns for extensibility
-- - Proper user isolation and cascade deletes
-- - Audit trails with created_at/updated_at timestamps
