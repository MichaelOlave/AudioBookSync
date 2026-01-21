"""Book download functionality."""

import asyncio
import os

from loguru import logger

from ..core.config import Config
from ..domain.progress import safe_progress_callback
from ..infrastructure.file_utils import (
    ensure_directory,
    file_exists_in_directory,
    normalize_filename,
)
from ..infrastructure.storage_service import StorageService


async def download_book(
    book: list,
    user_id: str,
    progress_callback=None,
) -> bool:
    """
    Download a book from Audible using the audible-cli tool.

    Args:
        book: List [asin, title]
        user_id: UUID of user for MinIO uploads (required)
        progress_callback: Optional async callable for progress updates.
                          Called with event_type and kwargs.

    Returns:
        True if successful, False otherwise
    """
    book_asin = book[0]
    book_title = book[1]

    # Validate user_id is provided (required for MinIO)
    if not user_id:
        logger.error("user_id is required for MinIO storage")
        return False

    try:
        logger.info(f"Starting download for {book_title}...")

        # Broadcast download started
        await safe_progress_callback(
            progress_callback,
            event_type="download.started",
            asin=book_asin,
            filename=book_title,
        )

        await ensure_directory(Config.DOWNLOAD_DIR)

        command = [
            "audible",
            "download",
            "-o",
            Config.DOWNLOAD_DIR,
            "-a",
            book_asin,
            "--aax-fallback",
            "-f",
            "asin_ascii",
            "-y",
        ]

        logger.info(f"Command: {' '.join(command)}")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            stdout_text = stdout.decode().strip()
            if "No new files downloaded" in stdout_text:
                raise Exception("No new files downloaded")
            elif await validate_book(book):
                logger.success(f"{stdout_text}")

                # Upload to MinIO (native storage)
                await _upload_downloaded_file_to_minio(book_asin, book_title, user_id)

                # Broadcast download completed
                await safe_progress_callback(
                    progress_callback,
                    event_type="download.completed",
                    asin=book_asin,
                    filename=book_title,
                )

                return True
            else:
                raise Exception(f"Download failed for {book_title}: {stdout_text}")
        else:
            stderr_text = stderr.decode().strip()
            raise Exception(
                f"Download failed for {book_title} with code "
                f"{process.returncode} Error output: {stderr_text}"
            )

    except asyncio.TimeoutError:
        logger.error(f"Download timed out for {book_title}")

        # Broadcast download failed
        await safe_progress_callback(
            progress_callback,
            event_type="download.failed",
            asin=book_asin,
            filename=book_title,
            error="Download timed out",
        )

        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {book_title}: {e}")

        # Broadcast download failed
        await safe_progress_callback(
            progress_callback,
            event_type="download.failed",
            asin=book_asin,
            filename=book_title,
            error=str(e),
        )

        return False


async def _upload_downloaded_file_to_minio(book_asin: str, book_title: str, user_id: str) -> None:
    """
    Upload downloaded file to MinIO after successful download.

    Args:
        book_asin: Amazon Standard Identification Number
        book_title: Title of the book
        user_id: User UUID
    """
    try:
        # Find the downloaded file
        file_path = None
        for item in os.listdir(Config.DOWNLOAD_DIR):
            if book_asin in item:
                file_path = os.path.join(Config.DOWNLOAD_DIR, item)
                break

        if not file_path or not os.path.exists(file_path):
            logger.warning(f"Downloaded file not found for {book_asin}")
            return

        # Upload to MinIO
        storage_service = StorageService()
        success, object_key = storage_service.save_file(
            user_id=user_id,
            file_path=file_path,
            file_type="downloaded",
            asin=book_asin,
        )

        if success and object_key:
            logger.info(f"Successfully uploaded download to MinIO: {object_key}")
        else:
            logger.warning(f"Failed to upload download to MinIO for {book_asin}")

    except Exception as e:
        # Log error but don't fail the download
        logger.error(f"Error uploading download to MinIO: {e}")


async def validate_book(book: list) -> bool:
    """Validate that a book was downloaded successfully."""
    book_asin = book[0]
    book_title = normalize_filename(book[1])

    identifiers = [book_asin, book_title]
    if file_exists_in_directory(Config.DOWNLOAD_DIR, identifiers):
        logger.info(f"{book_title} exists.")
        return True
    return False
