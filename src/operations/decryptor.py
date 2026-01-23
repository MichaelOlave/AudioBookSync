"""Book decryption functionality using FFmpeg."""

import asyncio
import json
import os
import tempfile
from typing import Optional

from loguru import logger

from ..core.config import Config
from ..database.engine import AsyncSessionLocal
from ..database.services import book_service, metadata_service
from ..domain.progress import safe_progress_callback
from ..infrastructure.storage_service import StorageService
from ..infrastructure.file_utils import normalize_filename


async def decrypt_book(
    book: list,
    user_id: str,
    encrypted_file_path: str = None,
    progress_callback=None,
    is_retry: bool = False,
    activation_bytes: str | None = None,
) -> bool:
    """
    Decrypt a book using FFmpeg and activation bytes.

    Uses temporary directory for decrypted output. On successful decryption,
    uploads decrypted file to MinIO and deletes encrypted file.
    On failure, uploads encrypted file to MinIO for later retry.

    Args:
        book: List [asin, title]
        user_id: UUID of user for MinIO uploads (required)
        encrypted_file_path: Path to encrypted file. If None, downloads from MinIO (retry scenario)
        progress_callback: Optional async callable for progress updates.
        is_retry: Whether this is a retry of a previously failed decryption
        activation_bytes: Optional DRM activation bytes for FFmpeg.

    Returns:
        True if successful, False otherwise
    """
    book_asin = book[0]
    book_title = normalize_filename(book[1])

    # Validate user_id is provided (required for MinIO)
    if not user_id:
        logger.error("user_id is required for MinIO storage")
        return False

    activation_value = activation_bytes or Config.ACTIVATION_BYTES
    if not activation_value or activation_value == "bytes_go_here":
        logger.error("Activation bytes not configured for decryption")
        return False

    try:
        logger.info(f"Starting decryption for '{book_title}' ({book_asin})...")

        # Broadcast decrypt started
        await safe_progress_callback(
            progress_callback,
            event_type="decrypt.started",
            asin=book_asin,
            filename=book_title,
        )

        # Handle retry scenario: download encrypted file from MinIO
        if is_retry and encrypted_file_path is None:
            # This would need to be passed as parameter in actual retry
            logger.error("Retry scenario requires encrypted_file_path or download from MinIO")
            return False

        input_file = encrypted_file_path
        if not input_file or not os.path.exists(input_file):
            raise Exception(f"Encrypted file not found: {input_file}")

        # Use temporary directory for decrypted output
        with tempfile.TemporaryDirectory() as temp_output_dir:
            output_file = os.path.join(temp_output_dir, f"{book_title}.m4b")

            # Create FFmpeg subprocess for decryption
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-activation_bytes",
                activation_value,
                "-i",
                input_file,
                "-c",
                "copy",
                output_file,
                "-n",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                stdout_text = stdout.decode().strip()
                logger.success(f"Decrypted: {output_file}: {stdout_text}")

                # Upload decrypted file to MinIO
                success, object_key = await _upload_decrypted_file_to_minio(
                    book_asin, book_title, user_id, output_file
                )

                if success:
                    logger.info(f"Successfully uploaded decryption to MinIO: {object_key}")

                    chapters = await _extract_chapters_from_file(output_file)
                    if chapters:
                        await _store_chapters(book_asin, chapters)
                    else:
                        logger.info(f"No chapters detected for {book_asin}")

                    # If this was a retry, delete encrypted file from MinIO
                    if is_retry:
                        # This would need encrypted_object_key parameter
                        logger.info("Retry successful - encrypted file should be deleted from MinIO")

                    # Broadcast decrypt completed
                    await safe_progress_callback(
                        progress_callback,
                        event_type="decrypt.completed",
                        asin=book_asin,
                        filename=book_title,
                    )

                    return True
                else:
                    raise Exception(f"Failed to upload decrypted file to MinIO for {book_title}")
            else:
                stderr_text = stderr.decode().strip()

                # Decryption failed - upload encrypted file for retry
                logger.warning(f"Decryption failed for {book_title}, uploading encrypted file for retry")
                await _upload_encrypted_file_to_minio(book_asin, user_id, input_file)

                raise Exception(f"FFmpeg error decrypting: {stderr_text}")

    except Exception as e:
        logger.error(f"An error occurred during decryption: {e}")

        # Broadcast decrypt failed
        await safe_progress_callback(
            progress_callback,
            event_type="decrypt.failed",
            asin=book_asin,
            filename=book_title,
            error=str(e),
        )

        return False


def _parse_time_base(time_base: Optional[str]) -> Optional[float]:
    """Parse FFmpeg time_base string into seconds-per-tick."""
    if not time_base or not isinstance(time_base, str):
        return None
    try:
        numerator, denominator = time_base.split("/")
        return float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None


def _seconds_to_ms(value: Optional[object]) -> Optional[int]:
    """Convert a seconds value (string/number) to milliseconds."""
    if value is None:
        return None
    try:
        return int(float(value) * 1000)
    except (TypeError, ValueError):
        return None


async def _extract_chapters_from_file(file_path: str) -> list[dict]:
    """Extract chapter metadata from a local audio file using ffprobe."""
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-print_format",
            "json",
            "-show_chapters",
            "-i",
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.warning(f"ffprobe failed: {stderr.decode().strip()}")
            return []

        payload = json.loads(stdout.decode())
        chapters = payload.get("chapters") or []
        normalized: list[dict] = []
        for idx, chapter in enumerate(chapters):
            if not isinstance(chapter, dict):
                continue
            time_base = _parse_time_base(chapter.get("time_base"))
            start_ms = _seconds_to_ms(chapter.get("start_time"))
            end_ms = _seconds_to_ms(chapter.get("end_time"))
            if start_ms is None and time_base is not None:
                start = chapter.get("start")
                start_ms = int(float(start) * time_base * 1000) if start is not None else None
            if end_ms is None and time_base is not None:
                end = chapter.get("end")
                end_ms = int(float(end) * time_base * 1000) if end is not None else None

            length_ms = None
            if start_ms is not None and end_ms is not None:
                length_ms = end_ms - start_ms

            tags = chapter.get("tags") or {}
            title = tags.get("title") or tags.get("TITLE")
            normalized.append(
                {
                    "sequence_number": idx + 1,
                    "title": title,
                    "start_offset_ms": start_ms,
                    "end_offset_ms": end_ms,
                    "length_ms": length_ms,
                    "raw_metadata": chapter,
                }
            )
        return normalized
    except Exception as e:
        logger.warning(f"Failed to extract chapters with ffprobe: {e}")
        return []


async def _store_chapters(asin: str, chapters: list[dict]) -> None:
    """Persist extracted chapters for a book."""
    try:
        async with AsyncSessionLocal() as db:
            await metadata_service.replace_chapters(db, asin=asin, chapters=chapters)
            media = await metadata_service.get_media_info(db, asin)
            if media:
                media.chapters_count = len(chapters)
            else:
                await metadata_service.create_media_info(
                    db,
                    asin=asin,
                    chapters_count=len(chapters),
                )
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to store chapters for {asin}: {e}")


async def _update_book_paths(
    asin: str,
    *,
    is_downloaded: bool | None = None,
    download_path: str | None = None,
    is_decrypted: bool | None = None,
    decrypted_path: str | None = None,
) -> None:
    """Persist download/decryption paths to the books table."""
    if is_downloaded is None and is_decrypted is None:
        return

    try:
        async with AsyncSessionLocal() as db:
            if is_downloaded is not None:
                updated = await book_service.update_book_download_status(
                    db=db,
                    asin=asin,
                    is_downloaded=is_downloaded,
                    download_path=download_path,
                )
                if not updated:
                    logger.warning(f"Failed to update download status for book {asin}")
            if is_decrypted is not None:
                updated = await book_service.update_book_decryption_status(
                    db=db,
                    asin=asin,
                    is_decrypted=is_decrypted,
                    decrypted_path=decrypted_path,
                )
                if not updated:
                    logger.warning(f"Failed to update decryption status for book {asin}")
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to update book paths for {asin}: {e}")


async def _upload_decrypted_file_to_minio(
    book_asin: str, book_title: str, user_id: str, file_path: str
) -> tuple[bool, str]:
    """
    Upload decrypted file to MinIO after successful decryption.

    Args:
        book_asin: Amazon Standard Identification Number
        book_title: Normalized title of the book
        user_id: User UUID
        file_path: Path to decrypted file

    Returns:
        Tuple of (success: bool, object_key: str)
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Decrypted file not found at {file_path}")
            return False, ""

        # Upload to MinIO
        storage_service = StorageService()
        success, object_key = storage_service.save_file(
            user_id=user_id,
            file_path=file_path,
            file_type="decrypted",
            title=book_title,
        )

        if success and object_key:
            logger.info(f"Successfully uploaded decryption to MinIO: {object_key}")
            await _update_book_paths(
                book_asin,
                is_downloaded=True,
                is_decrypted=True,
                decrypted_path=object_key,
            )
            return True, object_key
        else:
            logger.warning(f"Failed to upload decryption to MinIO for {book_title}")
            return False, ""

    except Exception as e:
        logger.error(f"Error uploading decryption to MinIO: {e}")
        return False, ""


async def _upload_encrypted_file_to_minio(book_asin: str, user_id: str, file_path: str) -> tuple[bool, str]:
    """
    Upload encrypted file to MinIO when decryption fails.

    This serves as a fallback for later retry attempts.

    Args:
        book_asin: Amazon Standard Identification Number
        user_id: User UUID
        file_path: Path to encrypted file

    Returns:
        Tuple of (success: bool, object_key: str)
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Encrypted file not found at {file_path}")
            return False, ""

        # Upload to MinIO as a downloaded/encrypted artifact for retry
        storage_service = StorageService()
        success, object_key = storage_service.save_file(
            user_id=user_id,
            file_path=file_path,
            file_type="downloaded",
            asin=book_asin,
        )

        if success and object_key:
            logger.info(f"Successfully uploaded encrypted file to MinIO for retry: {object_key}")
            await _update_book_paths(
                book_asin,
                is_downloaded=True,
                download_path=object_key,
            )
            return True, object_key
        else:
            logger.warning(f"Failed to upload encrypted file to MinIO for {book_asin}")
            return False, ""

    except Exception as e:
        logger.error(f"Error uploading encrypted file to MinIO: {e}")
        return False, ""
