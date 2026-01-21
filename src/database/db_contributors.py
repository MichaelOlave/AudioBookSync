"""Database operations for contributors (authors, narrators, editors, etc.)."""

from typing import Dict, Optional

from loguru import logger

from .db_pool import db_pool as _db_pool


class ContributorOperations:
    """Database operations for contributor management."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_or_get_contributor(
        self,
        name: str,
        contributor_type: Optional[str] = None,
        audible_asin: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a new contributor or get existing one by name.

        Args:
            name: Contributor's name
            contributor_type: Type of contributor (author, narrator, editor, translator, etc.)
            audible_asin: Audible's ASIN for this contributor if available
            description: Brief description of contributor
            url: URL to Audible profile

        Returns:
            contributor_id if successful, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                # Check if contributor already exists
                cursor.execute(
                    "SELECT contributor_id FROM contributors WHERE name = %s AND type = %s",
                    (name, contributor_type),
                )
                existing = cursor.fetchone()
                if existing:
                    return str(existing["contributor_id"])

                # Create new contributor
                cursor.execute(
                    """
                    INSERT INTO contributors (name, type, audible_asin, description, url)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING contributor_id
                    """,
                    (name, contributor_type, audible_asin, description, url),
                )
                result = cursor.fetchone()
                contributor_id = str(result["contributor_id"]) if result else None
                logger.debug(f"Created contributor: {name} (ID: {contributor_id})")
                return contributor_id
        except Exception as e:
            logger.error(f"Failed to create/get contributor: {e}")
            return None

    def get_contributor_by_id(self, contributor_id: str) -> Optional[Dict]:
        """
        Get contributor by ID.

        Args:
            contributor_id: Contributor's UUID

        Returns:
            Contributor dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM contributors WHERE contributor_id = %s",
                    (contributor_id,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get contributor: {e}")
            return None

    def get_contributor_by_name(
        self, name: str, contributor_type: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get contributor by name and optional type.

        Args:
            name: Contributor's name
            contributor_type: Optional type filter

        Returns:
            Contributor dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                if contributor_type:
                    cursor.execute(
                        "SELECT * FROM contributors WHERE name = %s AND type = %s",
                        (name, contributor_type),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM contributors WHERE name = %s",
                        (name,),
                    )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get contributor by name: {e}")
            return None


# Singleton instance
contributor_ops = ContributorOperations()
