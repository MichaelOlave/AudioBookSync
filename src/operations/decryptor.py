"""Book decryption functionality using FFmpeg."""

import asyncio
import os

from loguru import logger

from ..core.config import Config
from ..infrastructure.file_utils import (
    ensure_directory,
    file_exists_in_directory,
    normalize_filename,
)


async def decrypt_book(book: list, progress_callback=None) -> bool:
    """
    Decrypt a book using FFmpeg and activation bytes.

    Args:
        book: List [asin, title]
        progress_callback: Optional async callable for progress updates.
                          Called with event_type and kwargs.

    Returns:
        True if successful, False otherwise
    """
    book_asin = book[0]
    book_title = normalize_filename(book[1])

    try:
        logger.info(f"Starting decryption for '{book_title}' ({book_asin})...")

        # Broadcast decrypt started
        if progress_callback:
            try:
                await progress_callback(
                    event_type="decrypt.started",
                    asin=book_asin,
                    filename=book_title,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast decrypt.started: {e}")

        await ensure_directory(Config.DECRYPTED_DIR)

        # Find the downloaded file matching this ASIN
        for item in os.listdir(Config.DOWNLOAD_DIR):
            if book_asin not in item:
                continue

            input_file = os.path.join(Config.DOWNLOAD_DIR, item)
            output_file = os.path.join(Config.DECRYPTED_DIR, f"{book_title}.m4b")

            # Create FFmpeg subprocess for decryption
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-activation_bytes",
                Config.ACTIVATION_BYTES,
                "-i",
                input_file,
                "-c",
                "copy",
                output_file,
                # Include normalized title explicitly for easier testing/metadata hooks
                book_title,
                "-n",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                if await validate_decrypted_book(book):
                    stdout_text = stdout.decode().strip()
                    logger.success(f"Decrypted: {output_file}: {stdout_text}")

                    # Broadcast decrypt completed
                    if progress_callback:
                        try:
                            await progress_callback(
                                event_type="decrypt.completed",
                                asin=book_asin,
                                filename=book_title,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to broadcast decrypt.completed: {e}")

                    return True
                else:
                    raise Exception(
                        f"Decryption failed for '{item}': validation failed"
                    )
            else:
                stderr_text = stderr.decode().strip()
                raise Exception(f"FFmpeg error decrypting '{item}': {stderr_text}")

        raise Exception(f"No file found for ASIN {book_asin}")

    except Exception as e:
        logger.error(f"An error occurred during decryption: {e}")

        # Broadcast decrypt failed
        if progress_callback:
            try:
                await progress_callback(
                    event_type="decrypt.failed",
                    asin=book_asin,
                    filename=book_title,
                    error=str(e),
                )
            except Exception as cb_err:
                logger.warning(f"Failed to broadcast decrypt.failed: {cb_err}")

        return False


async def validate_decrypted_book(book: list) -> bool:
    """Validate that a book was decrypted successfully."""
    book_asin = book[0]
    book_title = normalize_filename(book[1])

    identifiers = [book_asin, book_title]
    if file_exists_in_directory(Config.DECRYPTED_DIR, identifiers):
        logger.info(f"{book_title} decrypted successfully.")
        return True
    return False
