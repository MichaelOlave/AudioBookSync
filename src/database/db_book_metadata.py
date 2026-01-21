"""Database operations for flexible book metadata stored as JSON."""

import json
from typing import Any, Dict, Optional

from loguru import logger

from .db_pool import db_pool as _db_pool


class BookMetadataOperations:
    """Database operations for flexible JSON metadata storage."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_or_update_metadata(
        self,
        asin: str,
        origin_asin: Optional[str] = None,
        brand: Optional[str] = None,
        periodical_info: Optional[Dict] = None,
        relationships: Optional[Dict] = None,
        badges: Optional[list] = None,
        claim_code_url: Optional[str] = None,
        parent_asin: Optional[str] = None,
        sku: Optional[str] = None,
        rating_distribution: Optional[Dict] = None,
        custom_metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Create or update comprehensive metadata for a book.

        Args:
            asin: Book's ASIN
            origin_asin: Original ASIN if re-published
            brand: Audible brand/imprint
            periodical_info: Periodical info (issue_number, issue_date, etc.)
            relationships: Related products, sequels, series info
            badges: Content badges (Audible Exclusive, etc.)
            claim_code_url: Claim code URL if available
            parent_asin: Parent product ASIN if this is a child
            sku: Stock keeping unit
            rating_distribution: Distribution of ratings
            custom_metadata: Any additional custom metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO book_metadata_json (
                        asin, origin_asin, brand, periodical_info, relationships,
                        badges, claim_code_url, parent_asin, sku, rating_distribution,
                        custom_metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asin) DO UPDATE SET
                        origin_asin = EXCLUDED.origin_asin,
                        brand = EXCLUDED.brand,
                        periodical_info = EXCLUDED.periodical_info,
                        relationships = EXCLUDED.relationships,
                        badges = EXCLUDED.badges,
                        claim_code_url = EXCLUDED.claim_code_url,
                        parent_asin = EXCLUDED.parent_asin,
                        sku = EXCLUDED.sku,
                        rating_distribution = EXCLUDED.rating_distribution,
                        custom_metadata = EXCLUDED.custom_metadata
                    """,
                    (
                        asin,
                        origin_asin,
                        brand,
                        json.dumps(periodical_info) if periodical_info else None,
                        json.dumps(relationships) if relationships else None,
                        json.dumps(badges) if badges else None,
                        claim_code_url,
                        parent_asin,
                        sku,
                        (json.dumps(rating_distribution) if rating_distribution else None),
                        json.dumps(custom_metadata) if custom_metadata else None,
                    ),
                )
                logger.debug(f"Created/updated metadata for book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to create/update metadata: {e}")
            return False

    def get_metadata(self, asin: str) -> Optional[Dict]:
        """
        Get all metadata for a book.

        Args:
            asin: Book's ASIN

        Returns:
            Metadata dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM book_metadata_json WHERE asin = %s",
                    (asin,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return None

    def add_custom_metadata(
        self,
        asin: str,
        key: str,
        value: Any,
    ) -> bool:
        """
        Add or update a custom metadata field.

        Args:
            asin: Book's ASIN
            key: Metadata key
            value: Metadata value (will be JSON-encoded)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO book_metadata_json (asin, custom_metadata)
                    VALUES (%s, jsonb_build_object(%s, to_jsonb(%s)))
                    ON CONFLICT (asin) DO UPDATE SET
                        custom_metadata = jsonb_set(
                            COALESCE(book_metadata_json.custom_metadata, '{}'::jsonb),
                            ARRAY[%s],
                            to_jsonb(%s)
                        )
                    """,
                    (asin, key, value, key, value),
                )
                logger.debug(f"Added custom metadata '{key}' for book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to add custom metadata: {e}")
            return False

    def get_custom_metadata(self, asin: str) -> Optional[Dict]:
        """
        Get custom metadata for a book.

        Args:
            asin: Book's ASIN

        Returns:
            Custom metadata dict if found, empty dict otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT custom_metadata FROM book_metadata_json WHERE asin = %s",
                    (asin,),
                )
                result = cursor.fetchone()
                return result.get("custom_metadata") if result else None
        except Exception as e:
            logger.error(f"Failed to get custom metadata: {e}")
            return None

    def set_brand(self, asin: str, brand: str) -> bool:
        """
        Set the Audible brand/imprint for a book.

        Args:
            asin: Book's ASIN
            brand: Brand name

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO book_metadata_json (asin, brand)
                    VALUES (%s, %s)
                    ON CONFLICT (asin) DO UPDATE SET brand = %s
                    """,
                    (asin, brand, brand),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to set brand: {e}")
            return False

    def set_origin_asin(self, asin: str, origin_asin: str) -> bool:
        """
        Set the original ASIN if this book is a re-published version.

        Args:
            asin: Book's current ASIN
            origin_asin: Original ASIN

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO book_metadata_json (asin, origin_asin)
                    VALUES (%s, %s)
                    ON CONFLICT (asin) DO UPDATE SET origin_asin = %s
                    """,
                    (asin, origin_asin, origin_asin),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to set origin ASIN: {e}")
            return False

    def set_rating_distribution(self, asin: str, distribution: Dict) -> bool:
        """
        Set the rating distribution for a book.

        Args:
            asin: Book's ASIN
            distribution: Rating distribution dict {5: count, 4: count, ...}

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO book_metadata_json (asin, rating_distribution)
                    VALUES (%s, %s)
                    ON CONFLICT (asin) DO UPDATE SET rating_distribution = %s
                    """,
                    (asin, json.dumps(distribution), json.dumps(distribution)),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to set rating distribution: {e}")
            return False

    def add_badge(self, asin: str, badge_name: str, badge_info: Optional[Dict] = None) -> bool:
        """
        Add a content badge for a book.

        Args:
            asin: Book's ASIN
            badge_name: Badge name (e.g., "Audible Exclusive")
            badge_info: Additional badge information

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                badge_obj = {"name": badge_name, **(badge_info or {})}
                cursor.execute(
                    """
                    INSERT INTO book_metadata_json (asin, badges)
                    VALUES (%s, jsonb_build_array(to_jsonb(%s)))
                    ON CONFLICT (asin) DO UPDATE SET
                        badges = (
                            COALESCE(book_metadata_json.badges, '[]'::jsonb)
                            || jsonb_build_array(to_jsonb(%s))
                        )
                    """,
                    (asin, badge_obj, badge_obj),
                )
                logger.debug(f"Added badge '{badge_name}' to book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to add badge: {e}")
            return False


# Singleton instance
book_metadata_ops = BookMetadataOperations()
