"""Database operations for book companion materials (PDFs, images, etc.)."""

from typing import Dict, List, Optional

from loguru import logger

from .db_pool import db_pool as _db_pool


class CompanionMaterialOperations:
    """Database operations for companion materials."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def add_material(
        self,
        asin: str,
        material_type: str,
        url: str,
        title: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        mime_type: Optional[str] = None,
        sequence_number: Optional[int] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        Add a companion material for a book.

        Args:
            asin: Book's ASIN
            material_type: Type (pdf, image, transcript, supplemental, etc.)
            url: URL to the material
            title: Material title
            file_size_bytes: File size in bytes
            mime_type: MIME type (application/pdf, image/jpeg, etc.)
            sequence_number: Display order
            description: Description of material

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO companion_materials (
                        asin, material_type, url, title, file_size_bytes,
                        mime_type, sequence_number, description
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asin, url) DO NOTHING
                    """,
                    (
                        asin,
                        material_type,
                        url,
                        title,
                        file_size_bytes,
                        mime_type,
                        sequence_number,
                        description,
                    ),
                )
                logger.debug(f"Added {material_type} material for book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to add companion material: {e}")
            return False

    def get_materials(self, asin: str) -> List[Dict]:
        """
        Get all companion materials for a book.

        Args:
            asin: Book's ASIN

        Returns:
            List of material dicts
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM companion_materials
                    WHERE asin = %s
                    ORDER BY sequence_number, material_type
                    """,
                    (asin,),
                )
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Failed to get companion materials: {e}")
            return []

    def get_materials_by_type(self, asin: str, material_type: str) -> List[Dict]:
        """
        Get companion materials of a specific type for a book.

        Args:
            asin: Book's ASIN
            material_type: Material type (pdf, image, etc.)

        Returns:
            List of material dicts
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM companion_materials
                    WHERE asin = %s AND material_type = %s
                    ORDER BY sequence_number
                    """,
                    (asin, material_type),
                )
                return cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Failed to get materials by type: {e}")
            return []

    def get_pdfs(self, asin: str) -> List[Dict]:
        """
        Get PDF companion materials for a book.

        Args:
            asin: Book's ASIN

        Returns:
            List of PDF material dicts
        """
        return self.get_materials_by_type(asin, "pdf")

    def has_materials(self, asin: str) -> bool:
        """
        Check if a book has any companion materials.

        Args:
            asin: Book's ASIN

        Returns:
            True if materials exist, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) as count FROM companion_materials WHERE asin = %s",
                    (asin,),
                )
                result = cursor.fetchone()
                return result and result.get("count", 0) > 0
        except Exception as e:
            logger.error(f"Failed to check for materials: {e}")
            return False

    def remove_material(self, asin: str, url: str) -> bool:
        """
        Remove a companion material by URL.

        Args:
            asin: Book's ASIN
            url: Material URL

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM companion_materials
                    WHERE asin = %s AND url = %s
                    """,
                    (asin, url),
                )
                logger.debug(f"Removed companion material for book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove companion material: {e}")
            return False

    def remove_all_materials(self, asin: str) -> bool:
        """
        Remove all companion materials for a book.

        Args:
            asin: Book's ASIN

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "DELETE FROM companion_materials WHERE asin = %s",
                    (asin,),
                )
                logger.info(f"Removed all companion materials for book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove all materials: {e}")
            return False


# Singleton instance
companion_material_ops = CompanionMaterialOperations()
