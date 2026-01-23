"""Book download functionality."""

import asyncio
import os
import tempfile

from loguru import logger

from ..domain.progress import safe_progress_callback
from .decryptor import decrypt_book as decrypt_book_impl


async def download_book(
    book: list,
    user_id: str,
    progress_callback=None,
) -> bool:
    """
    Download a book from Audible using audible-cli and immediately decrypt it.

    Uses temporary directories for both encrypted and decrypted files.
    On successful decryption, uploads decrypted file to MinIO.
    On decryption failure, uploads encrypted file to MinIO as fallback for retry.

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

        # Use temporary directory for encrypted file
        with tempfile.TemporaryDirectory() as temp_dir:
            command = [
                "audible",
                "download",
                "-o",
                temp_dir,
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

                # Find the downloaded file
                downloaded_file_path = None
                for item in os.listdir(temp_dir):
                    if book_asin in item:
                        downloaded_file_path = os.path.join(temp_dir, item)
                        break

                if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                    raise Exception(f"Downloaded file not found for {book_asin}")

                logger.success(f"{stdout_text}")

                # Immediately attempt decryption with temp directories
                decrypt_success = await decrypt_book_impl(
                    book=book,
                    user_id=user_id,
                    encrypted_file_path=downloaded_file_path,
                    progress_callback=progress_callback,
                )

                if decrypt_success:
                    # Decryption succeeded - encrypted file will be cleaned up automatically
                    # Broadcast download completed
                    await safe_progress_callback(
                        progress_callback,
                        event_type="download.completed",
                        asin=book_asin,
                        filename=book_title,
                    )
                    return True
                else:
                    # Decryption failed - encrypted file was uploaded to MinIO for retry
                    logger.warning(f"Download succeeded but decryption failed for {book_title}")
                    await safe_progress_callback(
                        progress_callback,
                        event_type="download.completed",
                        asin=book_asin,
                        filename=book_title,
                    )
                    # Still return True as the download was successful, just decrypt failed
                    return True
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
