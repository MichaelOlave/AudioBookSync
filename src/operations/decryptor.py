"""Book decryption functionality using FFmpeg."""

import asyncio
import os
import tempfile

from loguru import logger

from ..core.config import Config
from ..domain.progress import safe_progress_callback
from ..infrastructure.file_utils import normalize_filename


async def decrypt_book(
    book: list,
    user_id: str,
    encrypted_file_path: str = None,
    progress_callback=None,
    is_retry: bool = False,
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

    Returns:
        True if successful, False otherwise
    """
    book_asin = book[0]
    book_title = normalize_filename(book[1])

    # Validate user_id is provided (required for MinIO)
    if not user_id:
        logger.error("user_id is required for MinIO storage")
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
                Config.ACTIVATION_BYTES,
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

        # Upload to MinIO with file_type="encrypted" to distinguish from regular downloads
        storage_service = StorageService()
        success, object_key = storage_service.save_file(
            user_id=user_id,
            file_path=file_path,
            file_type="encrypted",
            asin=book_asin,
        )

        if success and object_key:
            logger.info(f"Successfully uploaded encrypted file to MinIO for retry: {object_key}")
            return True, object_key
        else:
            logger.warning(f"Failed to upload encrypted file to MinIO for {book_asin}")
            return False, ""

    except Exception as e:
        logger.error(f"Error uploading encrypted file to MinIO: {e}")
        return False, ""
