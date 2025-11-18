-- =====================================================
-- AudioBookSync Sample Data
-- =====================================================
-- This file contains sample data for testing and development
-- Run this after schema.sql to populate the database with test data
-- =====================================================

-- Clean up existing sample data (optional)
-- DELETE FROM notifications WHERE user_id IN (SELECT user_id FROM users WHERE username LIKE 'demo_%');
-- DELETE FROM book_genres WHERE asin LIKE 'TEST%';
-- DELETE FROM books WHERE asin LIKE 'TEST%';
-- DELETE FROM users WHERE username LIKE 'demo_%';

-- =====================================================
-- SAMPLE USERS
-- =====================================================

INSERT INTO users (username, email, auth_file_path, activation_bytes, is_active)
VALUES
    ('demo_user1', 'demo1@audiobooksync.local', '/auth/demo1.json', 'c3f80507', true),
    ('demo_user2', 'demo2@audiobooksync.local', '/auth/demo2.json', 'a1b2c3d4', true),
    ('test_user', 'test@audiobooksync.local', '/auth/test.json', 'test1234', false)
ON CONFLICT (username) DO NOTHING;

-- Get user IDs for use in subsequent inserts
DO $$
DECLARE
    user1_id UUID;
    user2_id UUID;
BEGIN
    SELECT user_id INTO user1_id FROM users WHERE username = 'demo_user1';
    SELECT user_id INTO user2_id FROM users WHERE username = 'demo_user2';

    -- =====================================================
    -- SAMPLE BOOKS
    -- =====================================================

    INSERT INTO books (
        asin, user_id, title, author, narrator, series_name,
        purchase_date, runtime_min, rating, description, is_downloaded, is_decrypted
    )
    VALUES
        (
            'TEST001',
            user1_id,
            'The Martian',
            'Andy Weir',
            'R.C. Bray',
            NULL,
            '2024-01-15',
            658,
            4.8,
            'Six days ago, astronaut Mark Watney became one of the first people to walk on Mars. Now, he''s sure he''ll be the first person to die there.',
            true,
            true
        ),
        (
            'TEST002',
            user1_id,
            'Project Hail Mary',
            'Andy Weir',
            'Ray Porter',
            NULL,
            '2024-02-20',
            970,
            4.9,
            'Ryland Grace is the sole survivor on a desperate, last-chance mission—and if he fails, humanity and the earth itself will perish.',
            true,
            false
        ),
        (
            'TEST003',
            user1_id,
            'The Name of the Wind',
            'Patrick Rothfuss',
            'Nick Podehl',
            'The Kingkiller Chronicle',
            '2024-03-10',
            991,
            4.7,
            'The riveting first-person narrative of a young man who grows to be the most notorious magician his world has ever seen.',
            false,
            false
        ),
        (
            'TEST004',
            user2_id,
            'Atomic Habits',
            'James Clear',
            'James Clear',
            NULL,
            '2024-01-05',
            321,
            4.6,
            'Tiny Changes, Remarkable Results. No matter your goals, Atomic Habits offers a proven framework for improving every day.',
            true,
            true
        ),
        (
            'TEST005',
            user2_id,
            'Sapiens',
            'Yuval Noah Harari',
            'Derek Perkins',
            NULL,
            '2024-02-15',
            901,
            4.5,
            'From a renowned historian comes a groundbreaking narrative of humanity''s creation and evolution.',
            true,
            false
        )
    ON CONFLICT (asin) DO NOTHING;

    -- =====================================================
    -- SAMPLE DOWNLOAD STATUS
    -- =====================================================

    INSERT INTO download_status (
        asin, status, download_path, download_started_at,
        download_completed_at, attempt_number, file_size_bytes, download_format
    )
    VALUES
        (
            'TEST001',
            'completed',
            '/audiobooks/downloaded/TEST001.aax',
            CURRENT_TIMESTAMP - INTERVAL '2 days',
            CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '15 minutes',
            1,
            245000000,
            'AAX'
        ),
        (
            'TEST002',
            'completed',
            '/audiobooks/downloaded/TEST002.aaxc',
            CURRENT_TIMESTAMP - INTERVAL '1 day',
            CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '20 minutes',
            1,
            358000000,
            'AAXC'
        ),
        (
            'TEST003',
            'failed',
            NULL,
            CURRENT_TIMESTAMP - INTERVAL '3 hours',
            NULL,
            2,
            NULL,
            NULL
        ),
        (
            'TEST004',
            'completed',
            '/audiobooks/downloaded/TEST004.aax',
            CURRENT_TIMESTAMP - INTERVAL '5 days',
            CURRENT_TIMESTAMP - INTERVAL '5 days' + INTERVAL '10 minutes',
            1,
            125000000,
            'AAX'
        ),
        (
            'TEST005',
            'completed',
            '/audiobooks/downloaded/TEST005.aaxc',
            CURRENT_TIMESTAMP - INTERVAL '4 days',
            CURRENT_TIMESTAMP - INTERVAL '4 days' + INTERVAL '18 minutes',
            1,
            412000000,
            'AAXC'
        );

    -- =====================================================
    -- SAMPLE DECRYPTION STATUS
    -- =====================================================

    INSERT INTO decryption_status (
        asin, status, input_path, output_path, output_format,
        decryption_started_at, decryption_completed_at, duration_seconds
    )
    VALUES
        (
            'TEST001',
            'completed',
            '/audiobooks/downloaded/TEST001.aax',
            '/audiobooks/decrypted/TEST001.m4b',
            'm4b',
            CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '16 minutes',
            CURRENT_TIMESTAMP - INTERVAL '2 days' + INTERVAL '25 minutes',
            540
        ),
        (
            'TEST002',
            'failed',
            '/audiobooks/downloaded/TEST002.aaxc',
            NULL,
            'm4b',
            CURRENT_TIMESTAMP - INTERVAL '1 day' + INTERVAL '21 minutes',
            NULL,
            NULL
        ),
        (
            'TEST004',
            'completed',
            '/audiobooks/downloaded/TEST004.aax',
            '/audiobooks/decrypted/TEST004.m4b',
            'm4b',
            CURRENT_TIMESTAMP - INTERVAL '5 days' + INTERVAL '11 minutes',
            CURRENT_TIMESTAMP - INTERVAL '5 days' + INTERVAL '18 minutes',
            420
        ),
        (
            'TEST005',
            'decrypting',
            '/audiobooks/downloaded/TEST005.aaxc',
            '/audiobooks/decrypted/TEST005.m4b',
            'm4b',
            CURRENT_TIMESTAMP - INTERVAL '10 minutes',
            NULL,
            NULL
        );

    -- =====================================================
    -- SAMPLE SYNC HISTORY
    -- =====================================================

    INSERT INTO sync_history (
        user_id, sync_type, sync_started_at, sync_completed_at,
        duration_seconds, books_found, books_added, books_downloaded,
        books_decrypted, errors_count, status
    )
    VALUES
        (
            user1_id,
            'full',
            CURRENT_TIMESTAMP - INTERVAL '7 days',
            CURRENT_TIMESTAMP - INTERVAL '7 days' + INTERVAL '45 minutes',
            2700,
            3,
            3,
            2,
            1,
            1,
            'partial'
        ),
        (
            user2_id,
            'full',
            CURRENT_TIMESTAMP - INTERVAL '6 days',
            CURRENT_TIMESTAMP - INTERVAL '6 days' + INTERVAL '35 minutes',
            2100,
            2,
            2,
            2,
            1,
            0,
            'completed'
        ),
        (
            user1_id,
            'incremental',
            CURRENT_TIMESTAMP - INTERVAL '3 hours',
            CURRENT_TIMESTAMP - INTERVAL '3 hours' + INTERVAL '10 minutes',
            600,
            3,
            0,
            0,
            0,
            1,
            'failed'
        );

    -- =====================================================
    -- SAMPLE BOOK GENRES
    -- =====================================================

    -- Assign genres to books
    INSERT INTO book_genres (asin, genre_id)
    SELECT 'TEST001', genre_id FROM genres WHERE genre_name = 'Science Fiction'
    UNION ALL
    SELECT 'TEST002', genre_id FROM genres WHERE genre_name = 'Science Fiction'
    UNION ALL
    SELECT 'TEST003', genre_id FROM genres WHERE genre_name = 'Fantasy'
    UNION ALL
    SELECT 'TEST004', genre_id FROM genres WHERE genre_name = 'Self-Help'
    UNION ALL
    SELECT 'TEST005', genre_id FROM genres WHERE genre_name = 'History'
    ON CONFLICT DO NOTHING;

    -- =====================================================
    -- SAMPLE ERROR LOG
    -- =====================================================

    INSERT INTO error_log (
        user_id, asin, error_type, error_message, severity, resolved
    )
    VALUES
        (
            user1_id,
            'TEST003',
            'download_error',
            'Failed to download audiobook: Connection timeout',
            'error',
            false
        ),
        (
            user1_id,
            'TEST002',
            'decryption_error',
            'FFmpeg decryption failed: Invalid activation bytes',
            'error',
            false
        ),
        (
            user2_id,
            NULL,
            'api_error',
            'Audible API authentication failed: Token expired',
            'warning',
            true
        );

    -- =====================================================
    -- SAMPLE USER CONFIG
    -- =====================================================

    INSERT INTO user_config (user_id, config_key, config_value, data_type, description)
    VALUES
        (
            user1_id,
            'download_directory',
            '/audiobooks/downloaded',
            'path',
            'Default download directory for audiobooks'
        ),
        (
            user1_id,
            'decrypted_directory',
            '/audiobooks/decrypted',
            'path',
            'Default directory for decrypted audiobooks'
        ),
        (
            user1_id,
            'auto_decrypt',
            'true',
            'boolean',
            'Automatically decrypt after download'
        ),
        (
            user1_id,
            'output_format',
            'm4b',
            'string',
            'Preferred output format for decrypted files'
        ),
        (
            user2_id,
            'download_directory',
            '/home/user2/audiobooks',
            'path',
            'Default download directory for audiobooks'
        );

    -- =====================================================
    -- SAMPLE NOTIFICATIONS
    -- =====================================================

    INSERT INTO notifications (
        user_id, notification_type, event_type, title, message, is_read
    )
    VALUES
        (
            user1_id,
            'in_app',
            'download_failed',
            'Download Failed',
            'Failed to download "The Name of the Wind". Error: Connection timeout',
            false
        ),
        (
            user1_id,
            'in_app',
            'decryption_complete',
            'Decryption Complete',
            'Successfully decrypted "The Martian"',
            true
        ),
        (
            user2_id,
            'in_app',
            'sync_complete',
            'Sync Complete',
            'Library sync completed successfully. 2 books added.',
            true
        );

END $$;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Display sample data counts
SELECT 'Sample Data Summary' AS info;

SELECT
    'Users' AS table_name,
    COUNT(*) AS record_count
FROM users WHERE username LIKE 'demo_%' OR username = 'test_user'

UNION ALL

SELECT
    'Books' AS table_name,
    COUNT(*) AS record_count
FROM books WHERE asin LIKE 'TEST%'

UNION ALL

SELECT
    'Download Status' AS table_name,
    COUNT(*) AS record_count
FROM download_status WHERE asin LIKE 'TEST%'

UNION ALL

SELECT
    'Decryption Status' AS table_name,
    COUNT(*) AS record_count
FROM decryption_status WHERE asin LIKE 'TEST%'

UNION ALL

SELECT
    'Sync History' AS table_name,
    COUNT(*) AS record_count
FROM sync_history

UNION ALL

SELECT
    'Book Genres' AS table_name,
    COUNT(*) AS record_count
FROM book_genres WHERE asin LIKE 'TEST%'

UNION ALL

SELECT
    'Error Log' AS table_name,
    COUNT(*) AS record_count
FROM error_log

UNION ALL

SELECT
    'User Config' AS table_name,
    COUNT(*) AS record_count
FROM user_config

UNION ALL

SELECT
    'Notifications' AS table_name,
    COUNT(*) AS record_count
FROM notifications;

-- Display sample books with complete information
SELECT * FROM v_books_complete WHERE asin LIKE 'TEST%';

-- =====================================================
-- END OF SAMPLE DATA
-- =====================================================
