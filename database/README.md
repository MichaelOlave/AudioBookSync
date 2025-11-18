# AudioBookSync Database Documentation

## Overview

This directory contains the complete PostgreSQL database schema for the AudioBookSync application. The database is designed to replace the current CSV-based storage system with a robust, ACID-compliant relational database that supports multi-user environments, comprehensive tracking, and audit trails.

## Files

- **`schema.sql`** - Complete database schema with all tables, indexes, triggers, and views
- **`setup.sql`** - Initial database setup script (run first)
- **`migrate.py`** - Python migration tool for automated database setup
- **`sample_data.sql`** - Sample data for testing and development
- **`README.md`** - This documentation file

## Quick Start

### Option 1: Using the Python Migration Tool (Recommended)

```bash
# Install required dependency
pip install psycopg2-binary

# Run migration (creates database and schema)
python database/migrate.py

# With custom connection parameters
python database/migrate.py \
    --host localhost \
    --port 5432 \
    --user postgres \
    --password your_password \
    --database audiobooksync

# Fresh installation (WARNING: destroys existing data!)
python database/migrate.py --fresh

# Verify schema only
python database/migrate.py --verify
```

### Option 2: Using psql Command Line

```bash
# 1. Create the database
psql -U postgres -c "CREATE DATABASE audiobooksync;"

# 2. Run the schema
psql -U postgres -d audiobooksync -f database/schema.sql

# 3. (Optional) Load sample data
psql -U postgres -d audiobooksync -f database/sample_data.sql
```

### Option 3: Using Docker

```bash
# Start PostgreSQL container
docker run --name audiobooksync-db \
    -e POSTGRES_PASSWORD=your_password \
    -e POSTGRES_DB=audiobooksync \
    -p 5432:5432 \
    -d postgres:15

# Run schema
docker exec -i audiobooksync-db psql -U postgres -d audiobooksync < database/schema.sql
```

## Environment Variables

Set these environment variables for database connection:

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=audiobooksync
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
```

Or create a `.env` file in the project root:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=audiobooksync
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

## Database Schema

### Entity Relationship Diagram

```
Users (1) ────── (∞) Books
Users (1) ────── (∞) Sync_History
Users (1) ────── (∞) Error_Log
Users (1) ────── (∞) User_Config
Users (1) ────── (∞) Notifications

Books (1) ────── (∞) Download_Status
Books (1) ────── (∞) Decryption_Status
Books (∞) ────── (∞) Genres [via Book_Genres junction table]
```

### Core Tables

#### 1. **users**
Stores user account information and authentication details.

**Key Fields:**
- `user_id` (UUID, PK) - Unique user identifier
- `username` (VARCHAR, UNIQUE) - User's username
- `email` (VARCHAR, UNIQUE) - User's email address
- `auth_file_path` (VARCHAR) - Path to Audible authentication JSON
- `activation_bytes` (VARCHAR) - DRM activation bytes for decryption
- `last_sync_date` (TIMESTAMP) - Last successful sync

**Indexes:**
- `idx_users_username`, `idx_users_email`, `idx_users_is_active`

---

#### 2. **books**
Stores audiobook metadata from Audible library.

**Key Fields:**
- `asin` (VARCHAR, PK) - Amazon Standard Identification Number
- `user_id` (UUID, FK) - Owner of the audiobook
- `title` (VARCHAR) - Book title
- `author` (VARCHAR) - Author name
- `narrator` (VARCHAR) - Narrator name
- `series_name` (VARCHAR) - Series name (if applicable)
- `runtime_min` (INTEGER) - Runtime in minutes
- `is_downloaded` (BOOLEAN) - Download status flag
- `is_decrypted` (BOOLEAN) - Decryption status flag
- `checksum` (VARCHAR) - SHA256 checksum for integrity

**Indexes:**
- `idx_books_user_id`, `idx_books_title`, `idx_books_author`
- `idx_books_is_downloaded`, `idx_books_is_decrypted`

**Constraints:**
- Rating must be between 0 and 5
- Runtime must be positive

---

#### 3. **download_status**
Tracks download attempts and status for each audiobook.

**Key Fields:**
- `download_id` (UUID, PK)
- `asin` (VARCHAR, FK) - Reference to book
- `status` (VARCHAR) - pending, downloading, completed, failed, cancelled
- `download_path` (VARCHAR) - File system path
- `file_size_bytes` (BIGINT) - Downloaded file size
- `download_format` (VARCHAR) - AAX, AAXC, etc.
- `error_message` (TEXT) - Error details if failed

**Status Values:** `pending`, `downloading`, `completed`, `failed`, `cancelled`

---

#### 4. **decryption_status**
Tracks decryption attempts and status for downloaded audiobooks.

**Key Fields:**
- `decryption_id` (UUID, PK)
- `asin` (VARCHAR, FK) - Reference to book
- `status` (VARCHAR) - pending, decrypting, completed, failed, cancelled
- `output_format` (VARCHAR) - m4b, mp3, flac, aac
- `duration_seconds` (INTEGER) - Time taken to decrypt

**Supported Formats:** `m4b`, `mp3`, `flac`, `aac`

---

#### 5. **sync_history**
Audit trail of library synchronization runs.

**Key Fields:**
- `sync_id` (UUID, PK)
- `user_id` (UUID, FK)
- `sync_type` (VARCHAR) - full, incremental, manual
- `books_found`, `books_added`, `books_downloaded` (INTEGER) - Statistics
- `duration_seconds` (INTEGER) - Sync duration
- `status` (VARCHAR) - in_progress, completed, partial, failed

---

#### 6. **genres**
Hierarchical genre/category system.

**Key Fields:**
- `genre_id` (SERIAL, PK)
- `genre_name` (VARCHAR, UNIQUE)
- `parent_genre_id` (INTEGER, FK) - Self-referencing for hierarchy

**Default Genres:** Fiction, Non-Fiction, Mystery & Thriller, Science Fiction, Fantasy, Romance, Biography & Memoir, Self-Help, Business, History, Science & Technology, True Crime

---

#### 7. **book_genres** (Junction Table)
Many-to-many relationship between books and genres.

**Key Fields:**
- `book_genre_id` (UUID, PK)
- `asin` (VARCHAR, FK)
- `genre_id` (INTEGER, FK)

**Unique Constraint:** (asin, genre_id)

---

#### 8. **error_log**
Comprehensive error logging for debugging and monitoring.

**Key Fields:**
- `error_id` (UUID, PK)
- `user_id` (UUID, FK)
- `asin` (VARCHAR, FK) - Optional book reference
- `error_type` (VARCHAR) - download_error, decryption_error, api_error, etc.
- `severity` (VARCHAR) - info, warning, error, critical
- `resolved` (BOOLEAN) - Resolution status

**Error Types:**
- `download_error`
- `decryption_error`
- `api_error`
- `authentication_error`
- `file_system_error`
- `validation_error`
- `network_error`
- `unknown_error`

---

#### 9. **user_config**
User-specific configuration settings.

**Key Fields:**
- `config_id` (UUID, PK)
- `user_id` (UUID, FK)
- `config_key` (VARCHAR) - Configuration key
- `config_value` (TEXT) - Configuration value
- `data_type` (VARCHAR) - string, integer, boolean, json, path

**Common Config Keys:**
- `download_directory`
- `decrypted_directory`
- `auto_decrypt`
- `output_format`

---

#### 10. **notifications**
Notification history for user alerts.

**Key Fields:**
- `notification_id` (UUID, PK)
- `user_id` (UUID, FK)
- `notification_type` (VARCHAR) - email, webhook, desktop, in_app
- `event_type` (VARCHAR) - sync_complete, download_failed, etc.
- `is_read` (BOOLEAN)

---

### Database Views

#### **v_books_complete**
Complete book information with user details, latest download/decryption status, and genres.

```sql
SELECT * FROM v_books_complete WHERE user_id = 'your-user-id';
```

#### **v_sync_statistics**
Aggregated synchronization statistics per user.

```sql
SELECT * FROM v_sync_statistics WHERE username = 'your-username';
```

#### **v_error_summary**
Error statistics grouped by type and severity.

```sql
SELECT * FROM v_error_summary WHERE severity = 'critical';
```

---

### Triggers

The schema includes several automated triggers:

1. **Auto-update `updated_at` timestamps**
   - Triggers on `users`, `books`, `download_status`, `decryption_status`, `user_config`

2. **Auto-update book download status**
   - When `download_status.status` changes to 'completed', automatically updates `books.is_downloaded = true`

3. **Auto-update book decryption status**
   - When `decryption_status.status` changes to 'completed', automatically updates `books.is_decrypted = true`

---

## Common Queries

### Get User's Library with Status

```sql
SELECT
    b.asin,
    b.title,
    b.author,
    b.is_downloaded,
    b.is_decrypted,
    ARRAY_AGG(DISTINCT g.genre_name) as genres
FROM books b
LEFT JOIN book_genres bg ON b.asin = bg.asin
LEFT JOIN genres g ON bg.genre_id = g.genre_id
WHERE b.user_id = 'your-user-id'
GROUP BY b.asin, b.title, b.author, b.is_downloaded, b.is_decrypted;
```

### Find Failed Downloads

```sql
SELECT
    b.title,
    b.author,
    ds.error_message,
    ds.created_at
FROM download_status ds
JOIN books b ON ds.asin = b.asin
WHERE ds.status = 'failed'
ORDER BY ds.created_at DESC;
```

### Get Sync History for User

```sql
SELECT
    sync_started_at,
    sync_type,
    books_found,
    books_added,
    books_downloaded,
    books_decrypted,
    status,
    duration_seconds
FROM sync_history
WHERE user_id = 'your-user-id'
ORDER BY sync_started_at DESC
LIMIT 10;
```

### Find Unresolved Errors

```sql
SELECT
    error_type,
    severity,
    error_message,
    timestamp
FROM error_log
WHERE resolved = false
ORDER BY timestamp DESC;
```

### Library Statistics

```sql
SELECT
    COUNT(*) as total_books,
    SUM(CASE WHEN is_downloaded THEN 1 ELSE 0 END) as downloaded_count,
    SUM(CASE WHEN is_decrypted THEN 1 ELSE 0 END) as decrypted_count,
    SUM(runtime_min) as total_runtime_minutes,
    ROUND(SUM(runtime_min) / 60.0, 2) as total_runtime_hours
FROM books
WHERE user_id = 'your-user-id';
```

---

## Migration from CSV

To migrate existing CSV data to the database:

1. **Create a user:**
   ```sql
   INSERT INTO users (username, email, auth_file_path, activation_bytes)
   VALUES ('Michael', 'michael@example.com', '/path/to/Michael.json', 'c3f80507');
   ```

2. **Import books from CSV:**
   ```python
   import csv
   import psycopg2

   # Connect to database
   conn = psycopg2.connect(
       host='localhost',
       database='audiobooksync',
       user='postgres',
       password='your_password'
   )
   cur = conn.cursor()

   # Get user_id
   cur.execute("SELECT user_id FROM users WHERE username = 'Michael'")
   user_id = cur.fetchone()[0]

   # Import from CSV
   with open('audiobooks/test_library.csv', 'r') as f:
       reader = csv.DictReader(f)
       for row in reader:
           cur.execute("""
               INSERT INTO books (asin, user_id, title, purchase_date, runtime_min)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (asin) DO NOTHING
           """, (
               row['ASIN'],
               user_id,
               row['Title'],
               row['Purchase Date'],
               int(row['Runtime (minutes)'])
           ))

   conn.commit()
   cur.close()
   conn.close()
   ```

---

## Performance Considerations

### Indexes

The schema includes comprehensive indexes on:
- All foreign keys
- Frequently queried fields (status, dates)
- Search fields (title, author)
- Boolean flags (is_downloaded, is_decrypted)

### Composite Indexes

For common query patterns:
- `(user_id, is_downloaded)` on books
- `(user_id, is_decrypted)` on books
- `(asin, status)` on download_status and decryption_status

### Partial Indexes

For active records only:
- Downloads in 'pending' or 'downloading' status
- Decryptions in 'pending' or 'decrypting' status

---

## Backup and Restore

### Backup Database

```bash
# Full database backup
pg_dump -U postgres audiobooksync > audiobooksync_backup.sql

# Compressed backup
pg_dump -U postgres audiobooksync | gzip > audiobooksync_backup.sql.gz

# Schema only
pg_dump -U postgres --schema-only audiobooksync > schema_backup.sql

# Data only
pg_dump -U postgres --data-only audiobooksync > data_backup.sql
```

### Restore Database

```bash
# From SQL file
psql -U postgres audiobooksync < audiobooksync_backup.sql

# From compressed file
gunzip -c audiobooksync_backup.sql.gz | psql -U postgres audiobooksync
```

---

## Security Considerations

### Production Recommendations

1. **Encrypt activation_bytes field**
   - Use PostgreSQL `pgcrypto` extension
   - Store encrypted with application-level decryption

2. **Create separate roles**
   ```sql
   CREATE ROLE audiobooksync_app LOGIN PASSWORD 'secure_password';
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO audiobooksync_app;
   GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO audiobooksync_app;
   ```

3. **Enable SSL connections**
   - Configure PostgreSQL to require SSL
   - Use certificate-based authentication

4. **Row-level security** (optional)
   ```sql
   ALTER TABLE books ENABLE ROW LEVEL SECURITY;
   CREATE POLICY user_books_policy ON books
       FOR ALL
       USING (user_id = current_setting('app.current_user_id')::uuid);
   ```

5. **Audit logging**
   - Enable PostgreSQL audit logging
   - Monitor sensitive operations

---

## Maintenance

### Vacuum and Analyze

```sql
-- Vacuum and analyze all tables
VACUUM ANALYZE;

-- Specific table
VACUUM ANALYZE books;
```

### Index Maintenance

```sql
-- Rebuild indexes
REINDEX DATABASE audiobooksync;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Monitor Table Sizes

```sql
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Troubleshooting

### Connection Issues

```bash
# Test connection
psql -U postgres -h localhost -d audiobooksync

# Check PostgreSQL is running
sudo systemctl status postgresql

# Check port
sudo netstat -plnt | grep 5432
```

### Permission Issues

```sql
-- Grant all privileges to user
GRANT ALL PRIVILEGES ON DATABASE audiobooksync TO your_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO your_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO your_user;
```

### Reset Database

```bash
# Using migrate.py
python database/migrate.py --fresh

# Or manually
dropdb -U postgres audiobooksync
createdb -U postgres audiobooksync
psql -U postgres -d audiobooksync -f database/schema.sql
```

---

## Future Enhancements

Potential schema improvements:

1. **Chapters table** - Store chapter information
2. **Bookmarks table** - User playback positions
3. **Collections table** - User-created book collections
4. **Sharing table** - Share books between users
5. **Download queue** - Prioritized download queue
6. **Statistics table** - Listening statistics and analytics
7. **Wishlist table** - Track desired books
8. **Tags table** - Custom user tags for books

---

## Support

For issues or questions:
- Check the [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- Review the schema comments: `\d+ table_name` in psql
- Check error logs: `SELECT * FROM error_log ORDER BY timestamp DESC;`

---

## License

This schema is part of the AudioBookSync project. See the main LICENSE file for details.

---

**Last Updated:** 2025-11-18
**Schema Version:** 1.0
**PostgreSQL Version:** 12+
