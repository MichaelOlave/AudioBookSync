"""Book database operations."""

from typing import Dict, List, Optional

from loguru import logger

from .db_pool import DatabasePool  # noqa: F401
from .db_pool import db_pool as _db_pool


class BookOperations:
    """Database operations for book management."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def add_book(
        self,
        asin: str,
        user_id: str,
        title: str,
        purchase_date: Optional[str] = None,
        runtime_min: Optional[int] = None,
        author: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Add a new book to the library.

        Args:
            asin: Amazon Standard Identification Number
            user_id: User UUID
            title: Book title
            purchase_date: Purchase date (YYYY-MM-DD)
            runtime_min: Runtime in minutes
            author: Author name
            **kwargs: Additional metadata (narrator, series_name, description, rating)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO books (
                        asin, user_id, title, purchase_date, runtime_min, author,
                        narrator, series_name, description, rating
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asin) DO UPDATE SET
                        title = EXCLUDED.title,
                        purchase_date = EXCLUDED.purchase_date,
                        runtime_min = EXCLUDED.runtime_min,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        asin,
                        user_id,
                        title,
                        purchase_date,
                        runtime_min,
                        author,
                        kwargs.get("narrator"),
                        kwargs.get("series_name"),
                        kwargs.get("description"),
                        kwargs.get("rating"),
                    ),
                )
                logger.info(f"Added/updated book: {title} (ASIN: {asin})")
                return True
        except Exception as e:
            logger.error(f"Failed to add book: {e}")
            return False

    def add_book_with_metadata(
        self,
        asin: str,
        user_id: str,
        title: str,
        book_data: Dict,
        purchase_date: Optional[str] = None,
    ) -> bool:
        """
        Add book with comprehensive metadata from Audible API.

        This method orchestrates adding a book with full metadata from Audible API
        response, populating all 7 metadata tables:
        - contributors (authors, narrators)
        - media_info (codec, bitrate, sample_rate)
        - reading_progress
        - book_availability (licensing/rights)
        - companion_materials (PDFs, transcripts)
        - book_metadata_json (flexible JSONB storage)

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
                runtime_min=self._get_runtime_minutes(book_data),
                author=self._get_authors_string(book_data),
                narrator=self._get_narrators_string(book_data),
                subtitle=book_data.get("subtitle"),
                description=book_data.get("product_description"),
                rating=self._get_rating(book_data),
            )

            if not book_added:
                return False

            # Import metadata operations modules
            from .db_book_contributors import book_contributor_ops
            from .db_book_metadata import book_metadata_ops
            from .db_companion_materials import companion_material_ops
            from .db_contributors import contributor_ops
            from .db_media_info import media_info_ops
            from .db_reading_progress import reading_progress_ops

            # 2. Add contributors (authors, narrators, editors)
            contributors_data = (
                book_data.get("authors", [])
                + book_data.get("narrators", [])
                + book_data.get("contributors", [])
            )
            for idx, contributor in enumerate(contributors_data):
                contrib_id = contributor_ops.create_or_get_contributor(
                    name=contributor.get("name"),
                    contributor_type=contributor.get("type", "author"),
                    audible_asin=contributor.get("asin"),
                )
                if contrib_id:
                    book_contributor_ops.add_book_contributor(
                        asin=asin,
                        contributor_id=contrib_id,
                        role=contributor.get("type", "author"),
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

            # 6. Store flexible metadata in JSONB
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

            logger.info(f"Added book with comprehensive metadata: {title} ({asin})")
            return True

        except Exception as e:
            logger.error(f"Failed to add book with metadata: {e}")
            return False

    def _get_runtime_minutes(self, book_data: Dict) -> Optional[int]:
        """Extract runtime in minutes from milliseconds."""
        runtime_ms = book_data.get("runtime_length_ms")
        if runtime_ms:
            return runtime_ms // 60000
        return None

    def _get_authors_string(self, book_data: Dict) -> Optional[str]:
        """Extract authors as comma-separated string for backward compatibility."""
        authors = [a.get("name", "") for a in book_data.get("authors", []) if a.get("name")]
        return ", ".join(authors) if authors else None

    def _get_narrators_string(self, book_data: Dict) -> Optional[str]:
        """Extract narrators as comma-separated string."""
        narrators = [n.get("name", "") for n in book_data.get("narrators", []) if n.get("name")]
        return ", ".join(narrators) if narrators else None

    def _get_rating(self, book_data: Dict) -> Optional[float]:
        """Extract average rating from API response."""
        rating_data = book_data.get("rating", {})
        distribution = rating_data.get("overall_distribution", {})
        if distribution:
            return distribution.get("average_rating")
        return None

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

    def remove_book(self, asin: str) -> bool:
        """
        Remove a book from the library.

        Args:
            asin: Amazon Standard Identification Number

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute("DELETE FROM books WHERE asin = %s", (asin,))
                logger.info(f"Removed book: {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove book: {e}")
            return False

    def get_user_books(self, user_id: str) -> List[Dict]:
        """
        Get all books for a user.

        Args:
            user_id: User's UUID

        Returns:
            List of book dicts
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM v_books_complete
                    WHERE user_id = %s
                    ORDER BY purchase_date DESC
                """,
                    (user_id,),
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get user books: {e}")
            return []

    def get_book_by_asin(self, asin: str) -> Optional[Dict]:
        """
        Get book details by ASIN.

        Args:
            asin: Amazon Standard Identification Number

        Returns:
            Book dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM v_books_complete WHERE asin = %s",
                    (asin,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get book: {e}")
            return None


# Singleton instance
book_ops = BookOperations()
