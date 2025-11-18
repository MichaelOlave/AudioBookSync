-- =====================================================
-- AudioBookSync PostgreSQL Database Schema
-- =====================================================
-- Version: 1.0
-- Description: Complete database schema for AudioBookSync application
-- This schema supports multi-user audiobook library management,
-- download tracking, decryption status, and comprehensive audit trails
-- =====================================================

-- Drop existing tables (in reverse order of dependencies)
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS user_config CASCADE;
DROP TABLE IF EXISTS error_log CASCADE;
DROP TABLE IF EXISTS book_genres CASCADE;
DROP TABLE IF EXISTS genres CASCADE;
DROP TABLE IF EXISTS sync_history CASCADE;
DROP TABLE IF EXISTS decryption_status CASCADE;
DROP TABLE IF EXISTS download_status CASCADE;
DROP TABLE IF EXISTS books CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- USERS TABLE
-- =====================================================
-- Stores user account information and authentication details
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    auth_file_path VARCHAR(500),
    activation_bytes VARCHAR(16),  -- DRM activation bytes (encrypted in production)
    is_active BOOLEAN DEFAULT true,
    last_sync_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for users table
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Comments for users table
COMMENT ON TABLE users IS 'Stores user account information for multi-user support';
COMMENT ON COLUMN users.activation_bytes IS 'Audible DRM activation bytes for decryption';
COMMENT ON COLUMN users.auth_file_path IS 'Path to Audible authentication JSON file';

-- =====================================================
-- BOOKS TABLE
-- =====================================================
-- Stores audiobook information from Audible library
CREATE TABLE books (
    asin VARCHAR(10) PRIMARY KEY,  -- Amazon Standard Identification Number
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    subtitle VARCHAR(500),
    author VARCHAR(500),
    narrator VARCHAR(500),
    series_name VARCHAR(300),
    series_sequence VARCHAR(50),
    publisher VARCHAR(200),
    publication_date DATE,
    purchase_date DATE,
    description TEXT,
    language VARCHAR(50) DEFAULT 'en-US',
    runtime_min INTEGER,
    rating DECIMAL(3,2),  -- e.g., 4.75
    review_count INTEGER DEFAULT 0,
    cover_art_url VARCHAR(1000),
    file_size_bytes BIGINT,
    checksum VARCHAR(64),  -- SHA256 checksum for file integrity
    is_downloaded BOOLEAN DEFAULT false,
    is_decrypted BOOLEAN DEFAULT false,
    download_path VARCHAR(1000),
    decrypted_path VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_rating CHECK (rating >= 0 AND rating <= 5),
    CONSTRAINT chk_runtime CHECK (runtime_min > 0)
);

-- Indexes for books table
CREATE INDEX idx_books_user_id ON books(user_id);
CREATE INDEX idx_books_title ON books(title);
CREATE INDEX idx_books_author ON books(author);
CREATE INDEX idx_books_series ON books(series_name);
CREATE INDEX idx_books_purchase_date ON books(purchase_date);
CREATE INDEX idx_books_is_downloaded ON books(is_downloaded);
CREATE INDEX idx_books_is_decrypted ON books(is_decrypted);

-- Comments for books table
COMMENT ON TABLE books IS 'Stores audiobook information from Audible library';
COMMENT ON COLUMN books.asin IS 'Amazon Standard Identification Number (unique identifier)';
COMMENT ON COLUMN books.checksum IS 'SHA256 checksum for downloaded file integrity verification';

-- =====================================================
-- DOWNLOAD_STATUS TABLE
-- =====================================================
-- Tracks download attempts and status for each audiobook
CREATE TABLE download_status (
    download_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asin VARCHAR(10) NOT NULL REFERENCES books(asin) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    download_path VARCHAR(1000),
    download_started_at TIMESTAMP WITH TIME ZONE,
    download_completed_at TIMESTAMP WITH TIME ZONE,
    attempt_number INTEGER DEFAULT 1,
    file_size_bytes BIGINT,
    download_format VARCHAR(10),  -- AAX, AAXC, etc.
    error_message TEXT,
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_download_status CHECK (status IN ('pending', 'downloading', 'completed', 'failed', 'cancelled')),
    CONSTRAINT chk_attempt_number CHECK (attempt_number > 0)
);

-- Indexes for download_status table
CREATE INDEX idx_download_status_asin ON download_status(asin);
CREATE INDEX idx_download_status_status ON download_status(status);
CREATE INDEX idx_download_status_created_at ON download_status(created_at DESC);

-- Comments for download_status table
COMMENT ON TABLE download_status IS 'Tracks all download attempts for audiobooks';
COMMENT ON COLUMN download_status.error_details IS 'JSON field for structured error information';

-- =====================================================
-- DECRYPTION_STATUS TABLE
-- =====================================================
-- Tracks decryption attempts and status for each audiobook
CREATE TABLE decryption_status (
    decryption_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asin VARCHAR(10) NOT NULL REFERENCES books(asin) ON DELETE CASCADE,
    download_id UUID REFERENCES download_status(download_id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    input_path VARCHAR(1000),
    output_path VARCHAR(1000),
    output_format VARCHAR(10) DEFAULT 'm4b',  -- m4b, mp3, etc.
    decryption_started_at TIMESTAMP WITH TIME ZONE,
    decryption_completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    error_message TEXT,
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_decryption_status CHECK (status IN ('pending', 'decrypting', 'completed', 'failed', 'cancelled')),
    CONSTRAINT chk_output_format CHECK (output_format IN ('m4b', 'mp3', 'flac', 'aac'))
);

-- Indexes for decryption_status table
CREATE INDEX idx_decryption_status_asin ON decryption_status(asin);
CREATE INDEX idx_decryption_status_status ON decryption_status(status);
CREATE INDEX idx_decryption_status_created_at ON decryption_status(created_at DESC);

-- Comments for decryption_status table
COMMENT ON TABLE decryption_status IS 'Tracks all decryption attempts for downloaded audiobooks';
COMMENT ON COLUMN decryption_status.output_format IS 'Output audio format (m4b, mp3, flac, aac)';

-- =====================================================
-- SYNC_HISTORY TABLE
-- =====================================================
-- Tracks synchronization runs between Audible and local library
CREATE TABLE sync_history (
    sync_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    sync_type VARCHAR(20) NOT NULL DEFAULT 'full',
    sync_started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    books_found INTEGER DEFAULT 0,
    books_added INTEGER DEFAULT 0,
    books_removed INTEGER DEFAULT 0,
    books_downloaded INTEGER DEFAULT 0,
    books_decrypted INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_sync_type CHECK (sync_type IN ('full', 'incremental', 'manual')),
    CONSTRAINT chk_sync_status CHECK (status IN ('in_progress', 'completed', 'partial', 'failed', 'cancelled'))
);

-- Indexes for sync_history table
CREATE INDEX idx_sync_history_user_id ON sync_history(user_id);
CREATE INDEX idx_sync_history_status ON sync_history(status);
CREATE INDEX idx_sync_history_started_at ON sync_history(sync_started_at DESC);

-- Comments for sync_history table
COMMENT ON TABLE sync_history IS 'Audit trail of all library synchronization runs';
COMMENT ON COLUMN sync_history.sync_type IS 'Type of sync: full (all books), incremental (changes only), manual (user-triggered)';

-- =====================================================
-- GENRES TABLE
-- =====================================================
-- Stores audiobook categories and genres
CREATE TABLE genres (
    genre_id SERIAL PRIMARY KEY,
    genre_name VARCHAR(100) UNIQUE NOT NULL,
    parent_genre_id INTEGER REFERENCES genres(genre_id) ON DELETE SET NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for genres table
CREATE INDEX idx_genres_name ON genres(genre_name);
CREATE INDEX idx_genres_parent ON genres(parent_genre_id);

-- Comments for genres table
COMMENT ON TABLE genres IS 'Hierarchical genre/category system for audiobooks';
COMMENT ON COLUMN genres.parent_genre_id IS 'Allows for hierarchical genre structure (e.g., Fiction > Science Fiction)';

-- =====================================================
-- BOOK_GENRES TABLE (Junction Table)
-- =====================================================
-- Many-to-many relationship between books and genres
CREATE TABLE book_genres (
    book_genre_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asin VARCHAR(10) NOT NULL REFERENCES books(asin) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(asin, genre_id)
);

-- Indexes for book_genres table
CREATE INDEX idx_book_genres_asin ON book_genres(asin);
CREATE INDEX idx_book_genres_genre_id ON book_genres(genre_id);

-- Comments for book_genres table
COMMENT ON TABLE book_genres IS 'Junction table for many-to-many relationship between books and genres';

-- =====================================================
-- ERROR_LOG TABLE
-- =====================================================
-- Comprehensive error logging for debugging and monitoring
CREATE TABLE error_log (
    error_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    asin VARCHAR(10) REFERENCES books(asin) ON DELETE SET NULL,
    sync_id UUID REFERENCES sync_history(sync_id) ON DELETE SET NULL,
    error_type VARCHAR(50) NOT NULL,
    error_code VARCHAR(20),
    error_message TEXT NOT NULL,
    error_details JSONB,
    stack_trace TEXT,
    severity VARCHAR(20) DEFAULT 'error',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,

    CONSTRAINT chk_error_type CHECK (error_type IN (
        'download_error', 'decryption_error', 'api_error',
        'authentication_error', 'file_system_error', 'validation_error',
        'network_error', 'unknown_error'
    )),
    CONSTRAINT chk_severity CHECK (severity IN ('info', 'warning', 'error', 'critical'))
);

-- Indexes for error_log table
CREATE INDEX idx_error_log_user_id ON error_log(user_id);
CREATE INDEX idx_error_log_asin ON error_log(asin);
CREATE INDEX idx_error_log_error_type ON error_log(error_type);
CREATE INDEX idx_error_log_severity ON error_log(severity);
CREATE INDEX idx_error_log_timestamp ON error_log(timestamp DESC);
CREATE INDEX idx_error_log_resolved ON error_log(resolved);

-- Comments for error_log table
COMMENT ON TABLE error_log IS 'Comprehensive error logging for debugging and system monitoring';
COMMENT ON COLUMN error_log.error_details IS 'JSON field for structured error context and additional information';

-- =====================================================
-- USER_CONFIG TABLE
-- =====================================================
-- Stores user-specific configuration settings
CREATE TABLE user_config (
    config_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    config_key VARCHAR(100) NOT NULL,
    config_value TEXT NOT NULL,
    data_type VARCHAR(20) DEFAULT 'string',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, config_key),
    CONSTRAINT chk_data_type CHECK (data_type IN ('string', 'integer', 'boolean', 'json', 'path'))
);

-- Indexes for user_config table
CREATE INDEX idx_user_config_user_id ON user_config(user_id);
CREATE INDEX idx_user_config_key ON user_config(config_key);

-- Comments for user_config table
COMMENT ON TABLE user_config IS 'User-specific configuration settings (download directory, output format preferences, etc.)';
COMMENT ON COLUMN user_config.data_type IS 'Type hint for parsing config_value';

-- =====================================================
-- NOTIFICATIONS TABLE
-- =====================================================
-- Stores notification history (for future features)
CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    is_read BOOLEAN DEFAULT false,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT chk_notification_type CHECK (notification_type IN ('email', 'webhook', 'desktop', 'in_app')),
    CONSTRAINT chk_event_type CHECK (event_type IN (
        'sync_complete', 'sync_failed', 'download_complete',
        'download_failed', 'decryption_complete', 'decryption_failed',
        'error_occurred', 'new_book_available'
    ))
);

-- Indexes for notifications table
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_type ON notifications(notification_type);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_sent_at ON notifications(sent_at DESC);

-- Comments for notifications table
COMMENT ON TABLE notifications IS 'Notification history for user alerts and system events';

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Auto-update updated_at timestamp on users table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_books_updated_at BEFORE UPDATE ON books
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_download_status_updated_at BEFORE UPDATE ON download_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_decryption_status_updated_at BEFORE UPDATE ON decryption_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_config_updated_at BEFORE UPDATE ON user_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-update book status when download completes
CREATE OR REPLACE FUNCTION update_book_download_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE books
        SET is_downloaded = true,
            download_path = NEW.download_path,
            file_size_bytes = NEW.file_size_bytes,
            updated_at = CURRENT_TIMESTAMP
        WHERE asin = NEW.asin;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_book_download_status
    AFTER UPDATE ON download_status
    FOR EACH ROW EXECUTE FUNCTION update_book_download_status();

-- Auto-update book status when decryption completes
CREATE OR REPLACE FUNCTION update_book_decryption_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE books
        SET is_decrypted = true,
            decrypted_path = NEW.output_path,
            updated_at = CURRENT_TIMESTAMP
        WHERE asin = NEW.asin;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_book_decryption_status
    AFTER UPDATE ON decryption_status
    FOR EACH ROW EXECUTE FUNCTION update_book_decryption_status();

-- =====================================================
-- VIEWS
-- =====================================================

-- View: Complete book information with latest status
CREATE OR REPLACE VIEW v_books_complete AS
SELECT
    b.*,
    u.username,
    u.email,
    ds_latest.status as latest_download_status,
    ds_latest.download_completed_at as last_download_date,
    dec_latest.status as latest_decryption_status,
    dec_latest.decryption_completed_at as last_decryption_date,
    ARRAY_AGG(DISTINCT g.genre_name) as genres
FROM books b
JOIN users u ON b.user_id = u.user_id
LEFT JOIN LATERAL (
    SELECT status, download_completed_at
    FROM download_status
    WHERE asin = b.asin
    ORDER BY created_at DESC
    LIMIT 1
) ds_latest ON true
LEFT JOIN LATERAL (
    SELECT status, decryption_completed_at
    FROM decryption_status
    WHERE asin = b.asin
    ORDER BY created_at DESC
    LIMIT 1
) dec_latest ON true
LEFT JOIN book_genres bg ON b.asin = bg.asin
LEFT JOIN genres g ON bg.genre_id = g.genre_id
GROUP BY b.asin, u.username, u.email, ds_latest.status,
         ds_latest.download_completed_at, dec_latest.status,
         dec_latest.decryption_completed_at;

COMMENT ON VIEW v_books_complete IS 'Complete book information with user details, latest status, and genres';

-- View: Sync statistics per user
CREATE OR REPLACE VIEW v_sync_statistics AS
SELECT
    u.user_id,
    u.username,
    COUNT(sh.sync_id) as total_syncs,
    SUM(sh.books_added) as total_books_added,
    SUM(sh.books_downloaded) as total_books_downloaded,
    SUM(sh.books_decrypted) as total_books_decrypted,
    SUM(sh.errors_count) as total_errors,
    MAX(sh.sync_started_at) as last_sync_date,
    AVG(sh.duration_seconds) as avg_sync_duration_seconds
FROM users u
LEFT JOIN sync_history sh ON u.user_id = sh.user_id
GROUP BY u.user_id, u.username;

COMMENT ON VIEW v_sync_statistics IS 'Aggregated synchronization statistics per user';

-- View: Error summary
CREATE OR REPLACE VIEW v_error_summary AS
SELECT
    error_type,
    severity,
    COUNT(*) as error_count,
    COUNT(DISTINCT user_id) as affected_users,
    COUNT(DISTINCT asin) as affected_books,
    MAX(timestamp) as last_occurrence,
    SUM(CASE WHEN resolved THEN 1 ELSE 0 END) as resolved_count,
    SUM(CASE WHEN NOT resolved THEN 1 ELSE 0 END) as unresolved_count
FROM error_log
GROUP BY error_type, severity
ORDER BY error_count DESC;

COMMENT ON VIEW v_error_summary IS 'Aggregated error statistics by type and severity';

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert common genres
INSERT INTO genres (genre_name, parent_genre_id, description) VALUES
    ('Fiction', NULL, 'Fictional narratives'),
    ('Non-Fiction', NULL, 'Factual content'),
    ('Mystery & Thriller', 1, 'Mystery and thriller fiction'),
    ('Science Fiction', 1, 'Science fiction'),
    ('Fantasy', 1, 'Fantasy fiction'),
    ('Romance', 1, 'Romance fiction'),
    ('Biography & Memoir', 2, 'Life stories and memoirs'),
    ('Self-Help', 2, 'Personal development'),
    ('Business', 2, 'Business and economics'),
    ('History', 2, 'Historical content'),
    ('Science & Technology', 2, 'Science and technology'),
    ('True Crime', NULL, 'True crime stories');

-- =====================================================
-- GRANTS (adjust based on your security requirements)
-- =====================================================
-- Example: Create read-only and read-write roles

-- Create roles (uncomment if needed)
-- CREATE ROLE audiobooksync_readonly;
-- CREATE ROLE audiobooksync_readwrite;

-- Grant permissions (uncomment and adjust as needed)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO audiobooksync_readonly;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO audiobooksync_readwrite;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO audiobooksync_readwrite;

-- =====================================================
-- PERFORMANCE INDEXES (Additional)
-- =====================================================

-- Composite indexes for common queries
CREATE INDEX idx_books_user_downloaded ON books(user_id, is_downloaded);
CREATE INDEX idx_books_user_decrypted ON books(user_id, is_decrypted);
CREATE INDEX idx_download_status_asin_status ON download_status(asin, status);
CREATE INDEX idx_decryption_status_asin_status ON decryption_status(asin, status);

-- Partial indexes for active records
CREATE INDEX idx_download_status_active ON download_status(asin)
    WHERE status IN ('pending', 'downloading');
CREATE INDEX idx_decryption_status_active ON decryption_status(asin)
    WHERE status IN ('pending', 'decrypting');

-- =====================================================
-- HELPFUL QUERIES (For reference)
-- =====================================================

-- Find books that failed to download
-- SELECT * FROM v_books_complete WHERE latest_download_status = 'failed';

-- Get sync history for a user
-- SELECT * FROM sync_history WHERE user_id = 'USER_UUID' ORDER BY sync_started_at DESC;

-- Find unresolved errors
-- SELECT * FROM error_log WHERE resolved = false ORDER BY timestamp DESC;

-- Get user's library statistics
-- SELECT
--     COUNT(*) as total_books,
--     SUM(CASE WHEN is_downloaded THEN 1 ELSE 0 END) as downloaded_count,
--     SUM(CASE WHEN is_decrypted THEN 1 ELSE 0 END) as decrypted_count,
--     SUM(runtime_min) as total_runtime_minutes
-- FROM books WHERE user_id = 'USER_UUID';

-- =====================================================
-- END OF SCHEMA
-- =====================================================
