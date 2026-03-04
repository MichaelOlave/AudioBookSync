# Database Enhancements: Comprehensive Audible Metadata Support

## Summary

The AudioBookSync database has been enhanced to support comprehensive metadata from the Audible API. The schema now includes normalized tables for contributors, media information, chapters, reading progress, book availability, companion materials, and flexible JSON storage for additional metadata.

## Configuration Changes

### Updated Response Groups

**File**: `src/core/config.py`

The `AUDIBLE_RESPONSE_GROUPS` has been expanded from the minimal 2 groups to 26+ groups covering all major Audible API data:

```python
"product_desc, product_attrs, contributors, media, series, "
"rating, reviews, categories, category_ladders, price, "
"cover_art_url, publisher, publication_date, origin_asin, "
"is_returnable, is_removable, is_archived, is_playable, "
"pdf_url, sku, badge_types, review_attrs, relationships, "
"percent_complete, last_position_heard, is_finished, "
"listening_status, claim_code_url"
```

**Data Captured**:
- Product information (description, attributes, pricing)
- All contributors (authors, narrators, editors, translators)
- Media technical details (codec, bitrate, sample rate, channels)
- Ratings and reviews
- Categories and hierarchical structure
- Reading progress and user status
- Availability and licensing information
- Companion materials (PDFs, etc.)
- Content badges and special information

## Database Schema Changes

### New Tables

#### 1. `contributors` Table
Stores information about book contributors (authors, narrators, editors, etc.)

**Columns**:
- `contributor_id` (UUID, PRIMARY KEY)
- `audible_asin` (VARCHAR(10), UNIQUE) - Audible's ID for the contributor
- `name` (VARCHAR(500))
- `type` (VARCHAR(50)) - "author", "narrator", "editor", "translator", etc.
- `description` (TEXT)
- `url` (VARCHAR(1000)) - Audible profile URL
- `created_at`, `updated_at` (TIMESTAMP)

**Indexes**: name, audible_asin

#### 2. `book_contributors` Table (Junction)
Links books to their contributors with role information

**Columns**:
- `book_contributor_id` (UUID, PRIMARY KEY)
- `asin` (FK to books)
- `contributor_id` (FK to contributors)
- `role` (VARCHAR(50)) - Specific role for this relationship
- `sequence_number` (INTEGER) - Display order
- `created_at` (TIMESTAMP)

**Unique Constraint**: asin + contributor_id + role

**Benefit**: Handles multiple authors/narrators correctly and maintains relationships

#### 3. `media_info` Table
Technical audio information

**Columns**:
- `media_id` (UUID, PRIMARY KEY)
- `asin` (FK to books, UNIQUE)
- `codec` (VARCHAR(50)) - AAC, MP3, FLAC, OGG, etc.
- `bitrate` (INTEGER) - bits per second
- `sample_rate` (INTEGER) - Hz (44100, 48000, etc.)
- `channels` (INTEGER) - Mono, stereo, 5.1, etc.
- `format_type` (VARCHAR(50)) - "audiobook", "podcast", "performance", etc.
- `duration_ms` (BIGINT) - Total duration in milliseconds
- `chapters_count` (INTEGER)
- `enhanced` (BOOLEAN) - Audible Enhanced Audio
- `created_at`, `updated_at` (TIMESTAMP)

**Benefit**: Separates technical audio info into dedicated table

#### 4. `reading_progress` Table
User's listening progress per book

**Columns**:
- `progress_id` (UUID, PRIMARY KEY)
- `asin`, `user_id` (FKs, UNIQUE together)
- `percent_complete` (INTEGER, 0-100)
- `position_ms` (BIGINT) - Last listening position in milliseconds
- `is_finished` (BOOLEAN)
- `date_started`, `date_finished`, `last_position_update` (TIMESTAMP)
- `created_at`, `updated_at` (TIMESTAMP)

**Benefit**: Tracks detailed reading progress and history per user

#### 5. `book_availability` Table
User's availability and rights for each book

**Columns**:
- `availability_id` (UUID, PRIMARY KEY)
- `asin` (FK to books, UNIQUE)
- `is_playable` (BOOLEAN)
- `is_returnable` (BOOLEAN) - Can be returned to Audible
- `is_removable` (BOOLEAN) - Can be deleted from library
- `is_archived` (BOOLEAN)
- `is_downloadable` (BOOLEAN)
- `license_status` (VARCHAR(50)) - "active", "expired", "revoked", etc.
- `expires_at` (TIMESTAMP) - License expiration if applicable
- `created_at`, `updated_at` (TIMESTAMP)

**Benefit**: Tracks licensing and availability status

#### 6. `companion_materials` Table
Supplementary materials (PDFs, images, transcripts, etc.)

**Columns**:
- `material_id` (UUID, PRIMARY KEY)
- `asin` (FK to books)
- `material_type` (VARCHAR(50)) - "pdf", "image", "transcript", "supplemental"
- `title`, `description` (VARCHAR/TEXT)
- `url` (VARCHAR(1000))
- `file_size_bytes` (BIGINT)
- `mime_type` (VARCHAR(100)) - "application/pdf", "image/jpeg", etc.
- `sequence_number` (INTEGER) - Display order
- `created_at` (TIMESTAMP)

**Unique Constraint**: asin + url

**Benefit**: Captures all companion materials available with a book

#### 7. `chapters` Table
Normalized per-chapter metadata for audiobooks.

**Columns**:
- `chapter_id` (UUID, PRIMARY KEY)
- `asin` (FK to books)
- `sequence_number` (INTEGER) - Chapter ordering
- `title` (VARCHAR(500))
- `start_offset_ms`, `end_offset_ms` (BIGINT) - Offsets in milliseconds
- `length_ms` (BIGINT)
- `raw_metadata` (JSONB) - Original chapter payload
- `created_at`, `updated_at` (TIMESTAMP)

**Unique Constraint**: asin + sequence_number

**Benefit**: Stores chapter-level data for precise navigation and display

#### 8. `book_metadata_json` Table
Flexible JSON storage for additional metadata

**Columns**:
- `metadata_id` (UUID, PRIMARY KEY)
- `asin` (FK to books, UNIQUE)
- `origin_asin` (VARCHAR(10)) - If this is re-published version
- `brand` (VARCHAR(100)) - Audible brand/imprint
- `periodical_info` (JSONB) - Issue number, date, etc.
- `relationships` (JSONB) - Related products, sequels, series
- `badges` (JSONB) - Content badges: [{"name": "Audible Exclusive", ...}]
- `claim_code_url` (VARCHAR(1000))
- `parent_asin` (VARCHAR(10)) - If this is a child product
- `sku` (VARCHAR(50)) - Stock keeping unit
- `rating_distribution` (JSONB) - {"5": 100, "4": 45, ...}
- `custom_metadata` (JSONB) - Extensible field for future data
- `created_at`, `updated_at` (TIMESTAMP)

**Benefit**: Flexible storage for complex nested data without schema changes

### Updated Existing Tables

#### `books` Table Additions
- `is_finished` (BOOLEAN) - Whether user finished the book
- `date_first_heard` (TIMESTAMP) - When user started listening
- `origin_asin` (VARCHAR(10)) - Cross-reference to metadata_json
- `brand` (VARCHAR(100)) - Cross-reference to metadata_json
- `metadata_json` (JSONB) - Fallback for other metadata

#### `genres` Table Additions
- `audible_category_id` (VARCHAR(50))
- `category_type` (VARCHAR(50)) - "genre", "category", "browse_node"
- `description` (TEXT)
- `popularity_rank` (INTEGER)

## New Views

### `v_books_with_metadata` View
Comprehensive view combining books with all related metadata

**Includes**:
- All book columns
- Aggregated contributors with roles
- Media information (codec, bitrate, channels, duration, etc.)
- Reading progress (percent complete, position, dates)
- Availability information (playable, returnable, license status)
- Aggregated companion materials
- Additional metadata (origin, brand, badges, etc.)

**Use Case**: API endpoints for returning complete book information

### `v_reading_statistics` View
User's reading statistics and progress summary

**Includes Per User**:
- Total books in library
- Books finished
- Books in progress
- Books not started
- Average progress percentage
- Last listened timestamp

**Use Case**: User statistics endpoints and dashboard

## Database Operations (New Python Modules)

### `src/database/db_contributors.py`
Operations for managing contributors

**Key Methods**:
- `create_or_get_contributor()` - Create or fetch existing contributor
- `get_contributor_by_id()`
- `get_contributor_by_name()`

### `src/database/db_book_contributors.py`
Operations for linking books to contributors

**Key Methods**:
- `add_book_contributor()` - Add contributor to book with role
- `get_book_contributors()` - Get all contributors for a book
- `get_contributors_by_role()` - Get specific role (authors, narrators, etc.)
- `update_contributor_sequence()` - Set display order
- `remove_book_contributor()`

### `src/database/db_media_info.py`
Operations for audio media information

**Key Methods**:
- `create_or_update_media_info()` - Store technical audio details
- `get_media_info()`
- `update_duration()`
- `update_chapters()`

### `src/database/db_reading_progress.py`
Operations for user reading progress

**Key Methods**:
- `create_progress()` - Start tracking progress
- `get_progress()` - Get user's progress on a book
- `update_progress()` - Update position/completion
- `mark_as_finished()` - Mark book as complete
- `get_user_reading_stats()` - Get statistics view
- `get_in_progress_books()` - Books currently being read
- `get_finished_books()` - Books user completed

### `src/database/db_book_availability.py`
Operations for book licensing and availability

**Key Methods**:
- `create_availability()` - Initialize availability record
- `get_availability()`
- `update_playable()`
- `update_returnable()`
- `update_removable()`
- `update_archived()`
- `set_license_status()` - Set status and expiration
- `get_expiring_licenses()` - Find licenses expiring soon

### `src/database/db_companion_materials.py`
Operations for companion materials

**Key Methods**:
- `add_material()` - Add PDF, transcript, etc.
- `get_materials()` - Get all materials for a book
- `get_materials_by_type()` - Get specific type
- `get_pdfs()` - Convenience method for PDFs
- `has_materials()` - Check if materials exist
- `remove_material()` - Remove by URL
- `remove_all_materials()`

### `src/database/db_book_metadata.py`
Operations for flexible JSON metadata

**Key Methods**:
- `create_or_update_metadata()` - Comprehensive update
- `get_metadata()`
- `add_custom_metadata()` - Add/update custom fields
- `get_custom_metadata()`
- `set_brand()`
- `set_origin_asin()`
- `set_rating_distribution()`
- `add_badge()` - Add content badge

## Migration Scripts

### `database/migrations/001_add_password_hash.sql`
Adds password authentication support for FastAPI

- Adds `password_hash` column to users table
- Creates indexes for authentication queries

### `database/migrations/002_add_comprehensive_metadata_tables.sql`
Comprehensive metadata tables and views

- Creates all 7 new tables
- Adds columns to existing tables (books, genres)
- Creates 2 views (v_books_with_metadata, v_reading_statistics)
- Creates triggers for auto-timestamp updates
- Creates trigger to auto-initialize book_availability

## Running the Migrations

```bash
# Apply password migration
psql -U postgres -d audiobooksync -f database/migrations/001_add_password_hash.sql

# Apply comprehensive metadata migration
psql -U postgres -d audiobooksync -f database/migrations/002_add_comprehensive_metadata_tables.sql
```

## Data Flow: Audible API → Database

### Example: Syncing a Book

1. **Fetch from Audible** (using 26+ response groups)
   ```python
   book_data = audible_client.get_library(response_groups)
   ```

2. **Extract and Store Data**:
   - **Book info** → `books` table (title, author, series, etc.)
   - **Contributors** → `contributors` + `book_contributors` (authors, narrators)
   - **Media** → `media_info` (codec, bitrate, channels, duration)
   - **Availability** → `book_availability` (rights, license status)
   - **Progress** → `reading_progress` (listening position, completion)
   - **Materials** → `companion_materials` (PDFs, transcripts)
   - **Metadata** → `book_metadata_json` (badges, origin, relationships)

3. **Query Complete Data** via `v_books_with_metadata` view

## Backward Compatibility

- All new columns and tables are **optional** (nullable/defaults)
- Existing queries continue to work
- New operations don't break existing code
- Migration is **additive only** (no dropping columns)

## Performance Optimizations

1. **Indexes on Foreign Keys**: Faster joins
2. **Unique Constraints**: Prevent duplicates
3. **Triggers for Auto-Updates**: Timestamp management
4. **Views for Complex Queries**: Pre-computed aggregations
5. **JSONB for Flexible Data**: Avoids schema changes

## Future Extensibility

1. **Custom Metadata Field**: Easily add new data to `book_metadata_json.custom_metadata`
2. **New Contributor Types**: Just insert new types into `contributors`
3. **Additional Material Types**: Support any companion material type
4. **Extended Progress Tracking**: Add new fields to `reading_progress` as needed

## Summary of Metadata Captured

| Category | Fields | Storage |
|----------|--------|---------|
| **Product Info** | Title, subtitle, series, rating | books table |
| **Contributors** | Authors, narrators, editors | contributors + junction |
| **Technical** | Codec, bitrate, sample rate, channels, duration | media_info |
| **User Progress** | Position, completion, start/end dates | reading_progress |
| **Licensing** | Playable, returnable, removable, license status | book_availability |
| **Materials** | PDFs, transcripts, images, supplements | companion_materials |
| **Flexible** | Badges, origin, relationships, periodicals | book_metadata_json |
| **Categories** | Genres, category hierarchy | genres + book_genres |

## Next Steps for FastAPI Integration

1. Use new database operations in service layer
2. Create Pydantic schemas that map to views
3. Implement endpoints to query `v_books_with_metadata`
4. Create progress tracking endpoints
5. Add contributor information to book responses
6. Implement reading statistics endpoints
