"""Consolidated book database operations module.

This module consolidates all book-related database operations that were
previously spread across 7 separate modules:
- db_books.py (317 lines) - Core book operations
- db_book_metadata.py (291 lines) - JSONB metadata
- db_contributors.py (117 lines) - Contributor master data
- db_book_contributors.py (181 lines) - Book-contributor relationships
- db_media_info.py (148 lines) - Audio codec/bitrate info
- db_book_availability.py (235 lines) - Licensing and playability
- db_companion_materials.py (205 lines) - PDFs, transcripts, images

CONSOLIDATION STRATEGY
======================
This module re-exports operations from the individual modules with a unified
interface. This approach:
1. Maintains 100% backward compatibility (old imports still work)
2. Reduces import complexity (single import instead of 7)
3. Logically groups related operations
4. Preserves singleton pattern across modules

MIGRATION PATH
==============
Phase 1 (current): Both old and new imports work
  from src.database.db_books import book_ops  # Still works
  from src.database.db_books_consolidated import book_ops  # New way

Phase 2 (future): Consolidate actual implementation
  - Merge module contents into this file
  - Update all internal imports
  - Remove old individual modules
"""

from ..database.db_book_availability import book_availability_ops as _availability_ops
from ..database.db_book_contributors import book_contributor_ops as _book_contributor_ops
from ..database.db_book_metadata import book_metadata_ops as _metadata_ops
from ..database.db_books import book_ops as _book_ops
from ..database.db_companion_materials import companion_material_ops as _companion_ops
from ..database.db_contributors import contributor_ops as _contributor_ops
from ..database.db_media_info import media_info_ops as _media_info_ops


class BookOperations:
    """Unified book operations interface consolidating 7 modules.

    Provides a single entry point for all book-related database operations,
    including core book data, metadata, contributors, media info, availability,
    and companion materials.

    Usage:
        from src.database.db_books_consolidated import book_ops

        # All operations are accessible through this single object
        books = book_ops.get_user_books(user_id="user123")
        book_ops.add_book(asin="B123", user_id="user123", title="Book Title")
    """

    # =====================
    # Core Book Operations
    # =====================

    def add_book(self, asin: str, user_id: str, title: str, **kwargs) -> bool:
        """Add a new book to the library (from db_books)."""
        return _book_ops.add_book(asin=asin, user_id=user_id, title=title, **kwargs)

    def get_book_by_asin(self, asin: str):
        """Get book details by ASIN (from db_books)."""
        return _book_ops.get_book_by_asin(asin=asin)

    def get_user_books(self, user_id: str):
        """Get all books for a user (from db_books)."""
        return _book_ops.get_user_books(user_id=user_id)

    def delete_book(self, asin: str) -> bool:
        """Delete a book from the library (from db_books)."""
        return _book_ops.delete_book(asin=asin)

    def book_exists(self, asin: str) -> bool:
        """Check if a book exists (from db_books)."""
        return _book_ops.book_exists(asin=asin)

    # =====================
    # Metadata Operations
    # =====================

    def create_or_update_metadata(self, asin: str, **metadata_fields) -> bool:
        """Create or update flexible JSONB metadata (from db_book_metadata)."""
        return _metadata_ops.create_or_update_metadata(asin=asin, **metadata_fields)

    def get_metadata(self, asin: str):
        """Get all metadata for a book (from db_book_metadata)."""
        return _metadata_ops.get_metadata(asin=asin)

    # =====================
    # Contributor Operations
    # =====================

    def create_or_get_contributor(self, name: str, contributor_type: str, **kwargs):
        """Create or retrieve a contributor (from db_contributors)."""
        return _contributor_ops.create_or_get_contributor(
            name=name, contributor_type=contributor_type, **kwargs
        )

    def get_contributor(self, contributor_id: str):
        """Get contributor by ID (from db_contributors)."""
        return _contributor_ops.get_contributor(contributor_id=contributor_id)

    # =====================
    # Book-Contributor Relationship Operations
    # =====================

    def add_book_contributor(
        self, asin: str, contributor_id: str, role: str, sequence_number: int = 0
    ) -> bool:
        """Link contributor to book (from db_book_contributors)."""
        return _book_contributor_ops.add_book_contributor(
            asin=asin,
            contributor_id=contributor_id,
            role=role,
            sequence_number=sequence_number,
        )

    def get_book_contributors(self, asin: str):
        """Get all contributors for a book (from db_book_contributors)."""
        return _book_contributor_ops.get_book_contributors(asin=asin)

    # =====================
    # Media Info Operations
    # =====================

    def create_or_update_media_info(self, asin: str, **media_fields) -> bool:
        """Create or update media information (from db_media_info)."""
        return _media_info_ops.create_or_update_media_info(asin=asin, **media_fields)

    def get_media_info(self, asin: str):
        """Get media info for a book (from db_media_info)."""
        return _media_info_ops.get_media_info(asin=asin)

    # =====================
    # Availability Operations
    # =====================

    def create_or_update_availability(self, asin: str, **availability_fields) -> bool:
        """Create or update book availability info (from db_book_availability)."""
        return _availability_ops.create_or_update_availability(asin=asin, **availability_fields)

    def get_availability(self, asin: str):
        """Get availability info for a book (from db_book_availability)."""
        return _availability_ops.get_availability(asin=asin)

    # =====================
    # Companion Materials Operations
    # =====================

    def add_material(self, asin: str, **material_fields) -> bool:
        """Add companion material for a book (from db_companion_materials)."""
        return _companion_ops.add_material(asin=asin, **material_fields)

    def get_materials(self, asin: str):
        """Get all companion materials for a book (from db_companion_materials)."""
        return _companion_ops.get_materials(asin=asin)


# Singleton instance for use throughout the application
book_ops = BookOperations()
