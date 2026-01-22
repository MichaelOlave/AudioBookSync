# Audible Metadata Mapping to Database

This document maps the Audible API metadata fields to the `book_metadata_json` table columns.

## Overview

The `book_metadata_json` table is designed to store comprehensive audiobook metadata from the Audible API. Fields are organized into logical categories:
- **Core Metadata**: Title, subtitle, language, publisher, format, status
- **Date Fields**: Publication, release, issue, and purchase dates
- **Audio Properties**: Runtime and codec information
- **Boolean Flags**: Availability and content indicators
- **Identifiers**: ASIN variants, SKU, ISBN
- **Complex Structures (JSON)**: Authors, narrators, ratings, images, codecs, library status, keywords
- **Legacy Fields**: For backward compatibility and flexible storage

## Field Mapping

### Core Metadata

| Audible Field | Database Column | Type | Description |
|---------------|-----------------|------|-------------|
| `title` | `title` | String(500) | Audiobook title |
| `subtitle` | `subtitle` | String(500) | Audiobook subtitle |
| `language` | `language` | String(50) | Language code (e.g., "english") |
| `publisher_name` | `publisher_name` | String(255) | Publisher name |
| `format_type` | `format_type` | String(50) | Format type (e.g., "unabridged") |
| `content_type` | `content_type` | String(50) | Content type (e.g., "Product") |
| `content_delivery_type` | `content_delivery_type` | String(50) | Delivery type (e.g., "MultiPartBook") |
| `status` | `status` | String(50) | Status (e.g., "Active") |

### Date Fields

| Audible Field | Database Column | Type | Description |
|---------------|-----------------|------|-------------|
| `publication_datetime` | `publication_datetime` | DateTime(TZ) | Publication timestamp |
| `release_date` | `release_date` | DateTime(TZ) | Release date (stored as datetime) |
| `issue_date` | `issue_date` | DateTime(TZ) | Issue date (stored as datetime) |
| `purchase_date` | `purchase_date` | DateTime(TZ) | Date added to library/purchased |

**Note**: Audible provides dates as ISO 8601 strings which are parsed to UTC timezone-aware datetimes.

### Audio Properties

| Audible Field | Database Column | Type | Description |
|---------------|-----------------|------|-------------|
| `runtime_length_min` | `runtime_length_min` | Integer | Total runtime in minutes |

### Boolean Flags

| Audible Field | Database Column | Type | Description |
|---------------|-----------------|------|-------------|
| `is_listenable` | `is_listenable` | Boolean | Whether audiobook can be played |
| `is_purchasability_suppressed` | `is_purchasability_suppressed` | Boolean | Whether purchase is hidden |
| `is_adult_product` | `is_adult_product` | Boolean | Adult content flag |
| `has_children` | `has_children` | Boolean | Has child products/parts |

### Identifiers

| Audible Field | Database Column | Type | Description |
|---------------|-----------------|------|-------------|
| `asin` | `asin` | String(10) | Primary Audible ASIN (FK to books.asin) |
| `origin_asin` | `origin_asin` | String(10) | Original ASIN if different |
| `sku` | `sku` | String(50) | Stock Keeping Unit |
| `isbn` | `isbn` | String(50) | ISBN if available |
| `parent_asin` | `parent_asin` | String(10) | Parent product ASIN (for series) |
| `brand` | `brand` | String(100) | Brand/publisher identifier |

### Complex Structures (JSON)

#### Authors

| Audible Field | Database Column | Type | Structure |
|---------------|-----------------|------|-----------|
| `authors` | `authors` | JSON | Array of objects with `asin` and `name` |

**Example**:
```json
[
  {
    "asin": "B0D1LQXYR8",
    "name": "Cerim"
  }
]
```

#### Narrators

| Audible Field | Database Column | Type | Structure |
|---------------|-----------------|------|-----------|
| `narrators` | `narrators` | JSON | Array of objects with `asin` and `name` |

**Example**:
```json
[
  {
    "asin": null,
    "name": "Henry Kramer"
  }
]
```

#### Rating

| Audible Field | Database Column | Type | Structure |
|---------------|-----------------|------|-----------|
| `rating` | `rating` | JSON | Object with review count and distribution stats |

**Example**:
```json
{
  "num_reviews": 315,
  "overall_distribution": {
    "average_rating": 4.038427167113494,
    "display_average_rating": "4.0",
    "display_stars": 4,
    "num_five_star_ratings": 629,
    "num_four_star_ratings": 186,
    "num_one_star_ratings": 91,
    "num_ratings": 1119,
    "num_three_star_ratings": 113,
    "num_two_star_ratings": 100
  },
  "performance_distribution": { ... },
  "story_distribution": { ... }
}
```

#### Product Images

| Audible Field | Database Column | Type | Structure |
|---------------|-----------------|------|-----------|
| `product_images` | `product_images` | JSON | Object mapping size to URL |

**Example**:
```json
{
  "500": "https://m.media-amazon.com/images/I/51YgbfM0T1L._SL500_.jpg"
}
```

#### Social Media Images

| Audible Field | Database Column | Type | Structure |
|---------------|-----------------|------|-----------|
| `social_media_images` | `social_media_images` | JSON | Object with platform-specific social images |

**Example**:
```json
{
  "facebook": "https://...",
  "ig_bg": "https://...",
  "ig_static_with_bg": "https://...",
  "ig_sticker": "https://...",
  "twitter": "https://..."
}
```

#### Available Codecs

| Audible Field | Database Column | Type | Structure |
|---------------|-----------------|------|-----------|
| `available_codecs` | `available_codecs` | JSON | Array of codec objects |

**Example**:
```json
[
  {
    "enhanced_codec": "LC_32_22050_stereo",
    "format": "Enhanced",
    "is_kindle_enhanced": true,
    "name": "aax_22_32"
  },
  {
    "enhanced_codec": "LC_64_44100_stereo",
    "format": "Enhanced",
    "is_kindle_enhanced": true,
    "name": "aax_44_64"
  }
]
```

#### Library Status

| Audible Field | Database Column | Type | Structure |
|---------------|-----------------|------|-----------|
| `library_status` | `library_status` | JSON | Object with user-specific library metadata |

**Example**:
```json
{
  "date_added": "2026-01-21T12:37:09.486Z",
  "is_pending": null,
  "is_preordered": null,
  "is_removable": null,
  "is_visible": null
}
```

#### Thesaurus Subject Keywords

| Audible Field | Database Column | Type | Structure |
|---------------|-----------------|------|-----------|
| `thesaurus_subject_keywords` | `thesaurus_subject_keywords` | JSON | Array of subject keywords |

**Example**:
```json
[
  "sword_&_sorcery",
  "literature-and-fiction"
]
```

### Legacy/Flexible Fields

| Audible Field | Database Column | Type | Description |
|---------------|-----------------|------|-------------|
| - | `periodical_info` | JSON | For periodical-specific metadata |
| - | `relationships` | JSON | For related products/books |
| - | `badges` | JSON | For achievement/badge data |
| - | `claim_code_url` | String(1000) | Claim code URL if available |
| - | `rating_distribution` | JSON | Deprecated: Use `rating` instead |
| - | `custom_metadata` | JSON | Flexible storage for custom fields |

### Audible Fields Not Yet Mapped

The following Audible fields are not currently mapped to specific columns. Consider adding if needed:

- `accolades` - Awards and accolades
- `amazon_asin` - Amazon ASIN (different from Audible ASIN)
- `asin_trends` - ASIN trend data
- `asset_badges`, `asset_details`, `badge_types` - Asset-related badges
- `audible_editors_summary` - Editor's summary
- `author_pages` - Author page information
- `availability` - Availability details
- `availability_codecs` - Codec availability (use `available_codecs`)
- `book_tags` - Genre/topic tags
- `buying_options` - Purchase options
- `category_ladders` - Category hierarchy
- `chart_ranks` - Chart ranking info
- `collection_ids` - Collections this book belongs to
- `content_level` - Content age/level rating
- `content_rating` - Content rating system
- `continuity` - Series continuity info
- `copyright` - Copyright holder
- `credits_required` - Subscription credits
- `customer_reviews` - Customer review data
- `customer_rights` - Rights info
- `date_first_available` - First available date
- `destination_asin` - Destination product
- `distribution_rights_region` - Rights region
- `editorial_reviews` - Editorial reviews
- `episode_count`, `episode_number`, `episode_type` - Podcast/series fields
- `extended_product_description` - Long description
- `generic_keyword` - Generic keywords
- `goodreads_ratings` - Goodreads integration
- `image_url` - Image URL (use `product_images`)
- `invites_remaining` - Family library invites
- `is_archived`, `is_ayce`, `is_buyable`, `is_downloaded`, `is_finished` - Various status flags
- `is_getting_latest_episodes` - Series subscription flag
- `is_in_wishlist` - Wishlist status
- `is_pdf_url_available` - PDF availability
- `is_pending`, `is_playable`, `is_preorderable`, `is_prereleased` - Status flags
- `is_released`, `is_removable`, `is_removable_by_parent`, `is_returnable`, `is_searchable` - Various flags
- `is_shared`, `is_visible` - Sharing/visibility flags
- `is_vvab`, `is_world_rights`, `is_ws4v_*` - Format-specific flags
- `library_status_badges` - Library status badges
- `listening_status` - Listening status
- `long_tail_topic_tags` - Topic tags
- `member_giving_status` - Member giving info
- `merchandising_description` - Merchandising text (consider if different from title/subtitle)
- `merchandising_summary` - Summary description
- `music_id` - Music identifier
- `narration_accent` - Narrator accent/language
- `new_episode_added_date` - Last episode date
- `order_id`, `order_item_id` - Order identifiers
- `participation_plans` - Subscription plans
- `pdf_url` - PDF document URL
- `percent_complete` - Reading progress
- `performance_summary` - Performance review
- `plans` - Subscription plan info
- `platinum_keywords` - Premium keywords
- `preorder_release_date`, `preorder_status` - Pre-order info
- `price` - Current price
- `product_page_url` - Audible product page URL
- `product_site_launch_date` - Site launch date
- `product_state` - Product state info
- `profile_sharing` - Profile sharing settings
- `program_participation` - Program enrollment
- `provided_review` - User's own review
- `review_keywords`, `review_status`, `review_summary` - Review info
- `rich_images` - Rich image data
- `right_type` - Rights type
- `sample_url` - Sample audio URL
- `season_number` - Series season
- `selected_sort_option_for_reviews`, `sort_options_for_reviews` - Review UI options
- `series` - Series information
- `shared_states`, `shared_with`, `shared_with_identity_directed_ids` - Sharing info
- `short_description` - Short description
- `spotlight_tags` - Spotlight tags
- `story_summary` - Story summary
- `subscription_asins` - Subscription variants
- `tags` - Miscellaneous tags
- `text_to_speech` - TTS capability
- `video_url` - Video URL
- `voice_description` - Voice/narrator description
- `ws4v_companion_asin`, `ws4v_details` - Companion format info

## Usage Examples

### Storing Audible Metadata

```python
from datetime import datetime
from src.database.models.book_metadata import BookMetadataJson

metadata = BookMetadataJson(
    asin="B0D2DXVBF1",
    title="Hell Difficulty Tutorial",
    subtitle="A LitRPG Adventure",
    language="english",
    publisher_name="Aethon Audio",
    format_type="unabridged",
    content_type="Product",
    content_delivery_type="MultiPartBook",
    status="Active",
    publication_datetime=datetime.fromisoformat("2024-05-14T07:00:00+00:00"),
    release_date=datetime.fromisoformat("2024-05-14"),
    issue_date=datetime.fromisoformat("2024-05-14"),
    purchase_date=datetime.fromisoformat("2026-01-21T12:37:09.486+00:00"),
    runtime_length_min=1114,
    is_listenable=True,
    is_purchasability_suppressed=False,
    is_adult_product=False,
    has_children=True,
    sku="BK_ACX0_396008",
    authors=[{"asin": "B0D1LQXYR8", "name": "Cerim"}],
    narrators=[{"asin": None, "name": "Henry Kramer"}],
    rating={
        "num_reviews": 315,
        "overall_distribution": {
            "average_rating": 4.038427167113494,
            "display_average_rating": "4.0",
            "display_stars": 4,
            # ... more fields
        },
        # ... more distributions
    },
    available_codecs=[
        {
            "enhanced_codec": "LC_32_22050_stereo",
            "format": "Enhanced",
            "is_kindle_enhanced": True,
            "name": "aax_22_32"
        }
    ],
    library_status={
        "date_added": "2026-01-21T12:37:09.486Z",
        "is_pending": None,
        "is_preordered": None,
        "is_removable": None,
        "is_visible": None
    },
    thesaurus_subject_keywords=["sword_&_sorcery", "literature-and-fiction"]
)
```

## Database Indexes

The following indexes are created for performance:
- `idx_book_metadata_asin` - Foreign key lookups
- `idx_book_metadata_title` - Title searches
- `idx_book_metadata_language` - Language filtering
- `idx_book_metadata_status` - Status filtering
- `idx_book_metadata_is_listenable` - Availability filtering

## Notes

1. **JSON Flexibility**: Complex structures are stored as JSON to accommodate Audible API changes without requiring schema modifications.

2. **Nullable Columns**: Most fields are nullable because not all audiobooks have all metadata available from Audible.

3. **DateTime Handling**: Date strings from Audible are parsed to timezone-aware UTC datetimes for consistency.

4. **Backward Compatibility**: Legacy fields like `rating_distribution` are retained for backward compatibility.

5. **Timestamps**: `created_at` and `updated_at` are automatically managed by the ORM.

## Migration

Run the migration to apply these changes to your database:

```bash
alembic upgrade head
```

To rollback:

```bash
alembic downgrade -1
```
