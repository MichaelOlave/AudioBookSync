# Metadata Integration Guide

## Overview

This guide explains how to integrate the new comprehensive metadata tables into your existing code, particularly when adding books from Audible API responses.

## File: `src/database/db_books.py`

### Current Implementation

The `add_book()` method in `BookOperations` currently accepts:

```python
def add_book(
    self,
    asin: str,
    user_id: str,
    title: str,
    purchase_date: Optional[date] = None,
    runtime_min: Optional[int] = None,
    author: Optional[str] = None,
    **kwargs  # Catches narrator, series_name, description, rating, etc.
) -> bool:
```

### Enhanced Implementation Required

To support the new metadata tables, the book creation flow should:

1. **Insert basic book info** → `books` table
2. **Extract and store contributors** → `contributors` + `book_contributors` tables
3. **Store media information** → `media_info` table
4. **Initialize availability** → `book_availability` table (auto via trigger)
5. **Create reading progress** → `reading_progress` table
6. **Store companion materials** → `companion_materials` table
7. **Store flexible metadata** → `book_metadata_json` table

### Enhanced Add Book Example

```python
# In src/database/db_books.py

from .db_contributors import contributor_ops, book_contributor_ops
from .db_media_info import media_info_ops
from .db_reading_progress import reading_progress_ops
from .db_book_metadata import book_metadata_ops
from .db_companion_materials import companion_material_ops

class BookOperations:

    def add_book_with_metadata(
        self,
        asin: str,
        user_id: str,
        title: str,
        book_data: Dict,  # Complete Audible API response
        purchase_date: Optional[date] = None,
    ) -> bool:
        """
        Add book with comprehensive metadata from Audible API.

        Args:
            asin: Book's ASIN
            user_id: User's UUID
            title: Book title
            book_data: Complete Audible API response with all response groups
            purchase_date: User's purchase date

        Returns:
            True if successful, False otherwise
        """
        try:
            # 1. Add basic book info
            book_added = self.add_book(
                asin=asin,
                user_id=user_id,
                title=title,
                purchase_date=purchase_date,
                runtime_min=book_data.get("runtime_length_ms", 0) // 60000,
                author=self._get_authors_string(book_data),
                subtitle=book_data.get("subtitle"),
                description=book_data.get("product_description"),
                rating=book_data.get("rating", {}).get("overall_distribution", {}).get("average_rating"),
                review_count=book_data.get("rating", {}).get("num_reviews"),
                cover_art_url=book_data.get("product_images", {}).get("500"),
                publisher=book_data.get("publisher_name"),
                publication_date=self._parse_date(book_data.get("release_date")),
                language=book_data.get("language"),
            )

            if not book_added:
                return False

            # 2. Add contributors (authors, narrators, etc.)
            contributors_data = book_data.get("authors", []) + book_data.get("narrators", [])
            for idx, contributor in enumerate(contributors_data):
                contrib_id = contributor_ops.create_or_get_contributor(
                    name=contributor.get("name"),
                    contributor_type=contributor.get("type"),  # "author", "narrator"
                    audible_asin=contributor.get("asin"),
                )
                if contrib_id:
                    book_contributor_ops.add_book_contributor(
                        asin=asin,
                        contributor_id=contrib_id,
                        role=contributor.get("type"),
                        sequence_number=idx,
                    )

            # 3. Add media information
            media_data = book_data.get("media_info", {})
            media_info_ops.create_or_update_media_info(
                asin=asin,
                codec=media_data.get("codec"),
                bitrate=media_data.get("bitrate"),
                sample_rate=media_data.get("sample_rate"),
                channels=media_data.get("channels"),
                format_type=book_data.get("content_type"),
                duration_ms=book_data.get("runtime_length_ms"),
                chapters_count=len(book_data.get("chapters", [])),
                enhanced=book_data.get("is_audible_enhanced", False),
            )

            # 4. Create reading progress record
            reading_progress_ops.create_progress(
                asin=asin,
                user_id=user_id,
                percent_complete=book_data.get("percent_complete", 0),
                position_ms=book_data.get("last_position_heard", 0),
            )

            # 5. Add companion materials
            for material in book_data.get("companion_materials", []):
                companion_material_ops.add_material(
                    asin=asin,
                    material_type=material.get("material_type", "document"),
                    url=material.get("url"),
                    title=material.get("title"),
                    file_size_bytes=material.get("file_size_bytes"),
                    mime_type=material.get("mime_type"),
                    description=material.get("description"),
                )

            # 6. Store flexible metadata
            book_metadata_ops.create_or_update_metadata(
                asin=asin,
                origin_asin=book_data.get("origin_asin"),
                brand=book_data.get("brand_name"),
                badges=book_data.get("content_badges"),
                claim_code_url=book_data.get("claim_code_url"),
                parent_asin=book_data.get("parent_asin"),
                sku=book_data.get("sku"),
                rating_distribution=self._get_rating_distribution(book_data),
                custom_metadata={
                    "content_type": book_data.get("content_type"),
                    "is_mp3": book_data.get("is_mp3"),
                    "is_audible_enhanced": book_data.get("is_audible_enhanced"),
                    "language_name": book_data.get("language_name"),
                },
            )

            logger.info(f"Added book with metadata: {title} ({asin})")
            return True

        except Exception as e:
            logger.error(f"Failed to add book with metadata: {e}")
            return False

    def _get_authors_string(self, book_data: Dict) -> Optional[str]:
        """Extract authors as comma-separated string (for backward compatibility)."""
        authors = [a["name"] for a in book_data.get("authors", [])]
        return ", ".join(authors) if authors else None

    def _get_rating_distribution(self, book_data: Dict) -> Optional[Dict]:
        """Extract rating distribution from API response."""
        rating_data = book_data.get("rating", {})
        distribution = rating_data.get("overall_distribution", {})
        if distribution:
            return {
                "5": distribution.get("5star_count", 0),
                "4": distribution.get("4star_count", 0),
                "3": distribution.get("3star_count", 0),
                "2": distribution.get("2star_count", 0),
                "1": distribution.get("1star_count", 0),
            }
        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse ISO date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        except:
            return None
```

## File: `src/operations/library_sync.py`

### Update the Sync Process

Modify `process_book()` to use the new enriched method:

```python
# In src/operations/library_sync.py

from ..database.db_books import book_ops

async def process_book(user_id: str, book_data: Dict, library_manager) -> None:
    """
    Process a single book: add to database with metadata, download, and decrypt.

    Args:
        user_id: User ID
        book_data: Complete book data from Audible API (with all response groups)
        library_manager: LibraryManager instance
    """
    asin = book_data["asin"]
    title = book_data["title"]

    try:
        logger.info(f"Processing book: {title}")

        # Add book WITH comprehensive metadata
        added = book_ops.add_book_with_metadata(
            asin=asin,
            user_id=user_id,
            title=title,
            book_data=book_data,  # Pass full API response
            purchase_date=library_manager.parse_purchase_date(book_data),
        )

        if not added:
            logger.warning(f"Book already exists or failed to add: {title}")
            # Continue with download/decrypt anyway

        # Download book
        download_success = await download_book([asin, title])
        if not download_success:
            raise Exception("Download failed")

        # Decrypt book
        decrypt_success = await decrypt_book([asin, title])
        if not decrypt_success:
            raise Exception("Decryption failed")

        # Update reading progress if user started listening
        from ..database.db_reading_progress import reading_progress_ops
        reading_progress_ops.update_progress(
            asin=asin,
            user_id=user_id,
            percent_complete=book_data.get("percent_complete", 0),
            position_ms=book_data.get("last_position_heard", 0),
        )

        logger.info(f"Successfully processed: {title}")

    except Exception as e:
        logger.error(f"Processing failed for {title}: {e}")
        await library_manager.log_error(
            error_type="sync_error",
            error_message=f"Failed to process book: {str(e)}",
            asin=asin,
            severity="error",
        )
```

## Audible API Response Mapping

Here's how Audible API fields map to your database tables:

### Book Basic Info → `books` table
```
API Field                   → DB Column
title                       → title
subtitle                    → subtitle
product_description         → description
authors[].name              → author (string, comma-separated)
narrators[].name            → narrator (string, comma-separated)
series_title                → series_name
series_position             → series_sequence
publisher_name              → publisher
release_date                → publication_date
runtime_length_ms / 60000   → runtime_min
rating.overall_distribution.average_rating → rating
rating.num_reviews          → review_count
product_images["500"]       → cover_art_url
language                    → language
```

### Contributors → `contributors` + `book_contributors`
```
API Field                   → DB Table
authors                     → contributors (type="author")
narrators                   → contributors (type="narrator")
contributors                → contributors (various types)
```

### Media Info → `media_info` table
```
API Field                   → DB Column
media_info.codec            → codec
media_info.bitrate          → bitrate
media_info.sample_rate      → sample_rate
media_info.channels         → channels
content_type                → format_type
runtime_length_ms           → duration_ms
chapters[]                  → chapters_count
is_audible_enhanced         → enhanced
```

### Chapters → `chapters` table
```
API Field                   → DB Column
chapters[].title            → title
chapters[].start_offset_ms  → start_offset_ms
chapters[].end_offset_ms    → end_offset_ms
chapters[].length_ms        → length_ms
chapters[]                  → sequence_number (order)
```

### Availability → `book_availability` table
```
API Field                   → DB Column
is_playable                 → is_playable
is_returnable               → is_returnable
is_removable                → is_removable
is_archived                 → is_archived
is_downloadable             → is_downloadable
(derived from API)          → license_status (default: "active")
```

### Reading Progress → `reading_progress` table
```
API Field                   → DB Column
percent_complete            → percent_complete
last_position_heard         → position_ms
is_finished                 → is_finished
(use current time)          → last_position_update
```

### Companion Materials → `companion_materials` table
```
API Field                   → DB Column
companion_materials[].type  → material_type
companion_materials[].url   → url
companion_materials[].title → title
companion_materials[].size  → file_size_bytes
companion_materials[].mime  → mime_type
```

### Flexible Metadata → `book_metadata_json` table
```
API Field                   → DB Column
origin_asin                 → origin_asin
brand_name                  → brand
content_badges              → badges
claim_code_url              → claim_code_url
parent_asin                 → parent_asin
sku                         → sku
rating.overall_distribution → rating_distribution
(all other fields)          → custom_metadata (JSON)
```

## Using the Comprehensive View

Query complete book data via `v_books_with_metadata`:

```python
# Example: Get complete book with all metadata
SELECT * FROM v_books_with_metadata WHERE asin = 'B001EXAMPLE';

# Result includes:
# - All book columns
# - contributors (JSON array with roles)
# - codec, bitrate, sample_rate, channels (media)
# - percent_complete, position_ms (progress)
# - is_playable, is_returnable, license_status (availability)
# - companion_materials (JSON array)
# - badges, origin_asin, rating_distribution (metadata)
```

## API Response Integration Example

When Audible API returns a book with response groups enabled:

```python
book_response = {
    "asin": "B001EXAMPLE",
    "title": "The Example Book",
    "subtitle": "A comprehensive guide",
    "product_description": "...",
    "authors": [
        {"asin": "B001AUTHOR1", "name": "John Doe", "type": "author"}
    ],
    "narrators": [
        {"asin": "B001NARRATOR1", "name": "Jane Voice", "type": "narrator"}
    ],
    "media_info": {
        "codec": "aac",
        "bitrate": 128000,
        "sample_rate": 44100,
        "channels": 2
    },
    "rating": {
        "overall_distribution": {
            "average_rating": 4.5,
            "5star_count": 100,
            "4star_count": 45,
            # ...
        },
        "num_reviews": 150
    },
    "companion_materials": [
        {
            "type": "pdf",
            "url": "https://...",
            "title": "Study Guide"
        }
    ],
    "content_badges": [
        {"name": "Audible Exclusive"}
    ],
    # ... 20+ more fields
}

# Simply pass to:
book_ops.add_book_with_metadata(asin, user_id, title, book_response)
```

## Testing the Integration

```python
# Test script to verify metadata is being stored

from src.database import (
    db_ops, contributor_ops, book_contributor_ops,
    media_info_ops, reading_progress_ops, book_availability_ops
)

asin = "B001TEST"

# Verify book exists
book = db_ops.books.get_book_by_asin(asin)
assert book is not None

# Verify contributors
contributors = book_contributor_ops.get_book_contributors(asin)
assert len(contributors) > 0

# Verify media info
media = media_info_ops.get_media_info(asin)
assert media is not None
assert media["codec"] is not None

# Verify reading progress
progress = reading_progress_ops.get_progress(asin, user_id)
assert progress is not None

# Verify availability
availability = book_availability_ops.get_availability(asin)
assert availability is not None

# Query via view
with db_pool.get_cursor() as cursor:
    cursor.execute(
        "SELECT * FROM v_books_with_metadata WHERE asin = %s",
        (asin,)
    )
    complete_book = cursor.fetchone()
    assert complete_book["contributors"] is not None
    assert complete_book["codec"] is not None
```

## Summary

The new metadata system provides:

1. **Normalized tables** for structured data (contributors, media, progress)
2. **Flexible JSONB storage** for complex/unstructured data
3. **Comprehensive views** for easy querying
4. **Backward compatible** - doesn't break existing code
5. **Extensible** - easy to add new fields or tables
6. **Well-indexed** - optimized for common queries

By implementing the `add_book_with_metadata()` method and updating the sync process, your database will capture the richness of Audible's API metadata while maintaining clean, normalized structure.
