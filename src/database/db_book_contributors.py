"""Database operations for book-contributor relationships."""

from typing import Dict, List, Optional
from loguru import logger

from .db_pool import db_pool as _db_pool


class BookContributorOperations:
    """Database operations for linking books to contributors."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def add_book_contributor(
        self,
        asin: str,
        contributor_id: str,
        role: str,
        sequence_number: Optional[int] = None,
    ) -> bool:
        """
        Add a contributor to a book.

        Args:
            asin: Book's ASIN
            contributor_id: Contributor's UUID
            role: Role type (author, narrator, editor, translator, etc.)
            sequence_number: Order of display (1st author, 2nd author, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO book_contributors (asin, contributor_id, role, sequence_number)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (asin, contributor_id, role) DO NOTHING
                    """,
                    (asin, contributor_id, role, sequence_number),
                )
                logger.debug(
                    f"Added contributor {contributor_id} to book {asin} as {role}"
                )
                return True
        except Exception as e:
            logger.error(f"Failed to add book contributor: {e}")
            return False

    def get_book_contributors(self, asin: str) -> List[Dict]:
        """
        Get all contributors for a book.

        Args:
            asin: Book's ASIN

        Returns:
            List of contributor dicts
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        bc.book_contributor_id,
                        bc.asin,
                        bc.contributor_id,
                        bc.role,
                        bc.sequence_number,
                        c.name,
                        c.type,
                        c.description,
                        c.url
                    FROM book_contributors bc
                    JOIN contributors c ON bc.contributor_id = c.contributor_id
                    WHERE bc.asin = %s
                    ORDER BY bc.sequence_number, c.name
                    """,
                    (asin,),
                )
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Failed to get book contributors: {e}")
            return []

    def get_contributors_by_role(self, asin: str, role: str) -> List[Dict]:
        """
        Get contributors for a book by specific role.

        Args:
            asin: Book's ASIN
            role: Role type (author, narrator, etc.)

        Returns:
            List of contributor dicts
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        c.contributor_id,
                        c.name,
                        c.type,
                        c.description,
                        c.url
                    FROM book_contributors bc
                    JOIN contributors c ON bc.contributor_id = c.contributor_id
                    WHERE bc.asin = %s AND bc.role = %s
                    ORDER BY bc.sequence_number, c.name
                    """,
                    (asin, role),
                )
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Failed to get contributors by role: {e}")
            return []

    def remove_book_contributor(
        self, asin: str, contributor_id: str, role: str
    ) -> bool:
        """
        Remove a contributor from a book.

        Args:
            asin: Book's ASIN
            contributor_id: Contributor's UUID
            role: Role type

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM book_contributors
                    WHERE asin = %s AND contributor_id = %s AND role = %s
                    """,
                    (asin, contributor_id, role),
                )
                logger.debug(f"Removed contributor {contributor_id} from book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove book contributor: {e}")
            return False

    def update_contributor_sequence(
        self, asin: str, contributor_id: str, sequence_number: int
    ) -> bool:
        """
        Update the sequence number for a contributor on a book.

        Args:
            asin: Book's ASIN
            contributor_id: Contributor's UUID
            sequence_number: New sequence number

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE book_contributors
                    SET sequence_number = %s
                    WHERE asin = %s AND contributor_id = %s
                    """,
                    (sequence_number, asin, contributor_id),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update contributor sequence: {e}")
            return False


# Singleton instance
book_contributor_ops = BookContributorOperations()
