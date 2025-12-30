"""Book download functionality."""

import asyncio

from loguru import logger

from ..core.config import Config
from ..infrastructure.file_utils import (
    ensure_directory,
    file_exists_in_directory,
    normalize_filename,
)


async def download_book(book: list, progress_callback=None) -> bool:
    """
    Download a book from Audible using the audible-cli tool.

    Args:
        book: List [asin, title]
        progress_callback: Optional async callable for progress updates.
                          Called with event_type and kwargs.

    Returns:
        True if successful, False otherwise
    """
    book_asin = book[0]
    book_title = book[1]

    try:
        logger.info(f"Starting download for {book_title}...")

        # Broadcast download started
        if progress_callback:
            try:
                await progress_callback(
                    event_type="download.started",
                    asin=book_asin,
                    filename=book_title,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast download.started: {e}")

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

                # Broadcast download completed
                if progress_callback:
                    try:
                        await progress_callback(
                            event_type="download.completed",
                            asin=book_asin,
                            filename=book_title,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to broadcast download.completed: {e}")

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
        if progress_callback:
            try:
                await progress_callback(
                    event_type="download.failed",
                    asin=book_asin,
                    filename=book_title,
                    error="Download timed out",
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast download.failed: {e}")

        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {book_title}: {e}")

        # Broadcast download failed
        if progress_callback:
            try:
                await progress_callback(
                    event_type="download.failed",
                    asin=book_asin,
                    filename=book_title,
                    error=str(e),
                )
            except Exception as cb_err:
                logger.warning(f"Failed to broadcast download.failed: {cb_err}")

        return False


async def validate_book(book: list) -> bool:
    """Validate that a book was downloaded successfully."""
    book_asin = book[0]
    book_title = normalize_filename(book[1])

    identifiers = [book_asin, book_title]
    if file_exists_in_directory(Config.DOWNLOAD_DIR, identifiers):
        logger.info(f"{book_title} exists.")
        return True
    return False
