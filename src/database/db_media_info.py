"""Database operations for media information (audio technical details)."""

from typing import Dict, Optional
from loguru import logger

from .db_pool import db_pool as _db_pool


class MediaInfoOperations:
    """Database operations for audio media information."""

    # Allow tests and callers to override the pool; default to shared singleton.
    db_pool = _db_pool

    def create_or_update_media_info(
        self,
        asin: str,
        codec: Optional[str] = None,
        bitrate: Optional[int] = None,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        format_type: Optional[str] = None,
        duration_ms: Optional[int] = None,
        chapters_count: Optional[int] = None,
        enhanced: Optional[bool] = None,
    ) -> bool:
        """
        Create or update media information for a book.

        Args:
            asin: Book's ASIN
            codec: Audio codec (AAC, MP3, FLAC, etc.)
            bitrate: Bitrate in bps
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            format_type: Format type (audiobook, podcast, performance, etc.)
            duration_ms: Total duration in milliseconds
            chapters_count: Number of chapters
            enhanced: Whether it has Audible Enhanced Audio

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO media_info (
                        asin, codec, bitrate, sample_rate, channels,
                        format_type, duration_ms, chapters_count, enhanced
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asin) DO UPDATE SET
                        codec = EXCLUDED.codec,
                        bitrate = EXCLUDED.bitrate,
                        sample_rate = EXCLUDED.sample_rate,
                        channels = EXCLUDED.channels,
                        format_type = EXCLUDED.format_type,
                        duration_ms = EXCLUDED.duration_ms,
                        chapters_count = EXCLUDED.chapters_count,
                        enhanced = EXCLUDED.enhanced
                    """,
                    (
                        asin,
                        codec,
                        bitrate,
                        sample_rate,
                        channels,
                        format_type,
                        duration_ms,
                        chapters_count,
                        enhanced,
                    ),
                )
                logger.debug(f"Created/updated media info for book {asin}")
                return True
        except Exception as e:
            logger.error(f"Failed to create/update media info: {e}")
            return False

    def get_media_info(self, asin: str) -> Optional[Dict]:
        """
        Get media information for a book.

        Args:
            asin: Book's ASIN

        Returns:
            Media info dict if found, None otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM media_info WHERE asin = %s",
                    (asin,),
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get media info: {e}")
            return None

    def update_duration(self, asin: str, duration_ms: int) -> bool:
        """
        Update the duration of a book's audio.

        Args:
            asin: Book's ASIN
            duration_ms: Duration in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE media_info SET duration_ms = %s WHERE asin = %s",
                    (duration_ms, asin),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update duration: {e}")
            return False

    def update_chapters(self, asin: str, chapters_count: int) -> bool:
        """
        Update the chapter count for a book.

        Args:
            asin: Book's ASIN
            chapters_count: Number of chapters

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db_pool.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE media_info SET chapters_count = %s WHERE asin = %s",
                    (chapters_count, asin),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update chapters: {e}")
            return False


# Singleton instance
media_info_ops = MediaInfoOperations()
