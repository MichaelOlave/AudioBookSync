"""Book download functionality."""

import asyncio
import json
import os
import tempfile

from loguru import logger

from ..domain.progress import safe_progress_callback
from .decryptor import decrypt_book as decrypt_book_impl


async def download_book(
    book: list,
    user_id: str,
    progress_callback=None,
    audible_auth: dict | None = None,
    activation_bytes: str | None = None,
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
        audible_auth: Audible auth.json data for audible-cli.
        activation_bytes: Optional DRM activation bytes for decryption.

    Returns:
        True if successful, False otherwise
    """
    book_asin = book[0]
    book_title = book[1]

    # Validate user_id is provided (required for MinIO)
    if not user_id:
        logger.error("user_id is required for MinIO storage")
        return False

    if not audible_auth:
        logger.error("Audible credentials not configured; cannot download")
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
            # Create isolated audible-cli config + auth file from DB auth
            with tempfile.TemporaryDirectory() as auth_dir:
                auth_path = os.path.join(auth_dir, "auth.json")
                config_path = os.path.join(auth_dir, "config.toml")

                with open(auth_path, "w", encoding="utf-8") as auth_file:
                    json.dump(audible_auth, auth_file)

                country_code = audible_auth.get("locale_code") or audible_auth.get("locale") or "us"
                config_contents = (
                    'title = "Audible Config File"\n\n'
                    "[APP]\n"
                    'primary_profile = "default"\n\n'
                    "[profile.default]\n"
                    'auth_file = "auth.json"\n'
                    f'country_code = "{country_code}"\n'
                )
                with open(config_path, "w", encoding="utf-8") as config_file:
                    config_file.write(config_contents)

                env = os.environ.copy()
                env["AUDIBLE_CONFIG_DIR"] = auth_dir

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
                    env=env,
                )

                # Monitor file size while download is in progress
                async def monitor_download():
                    """Monitor temporary directory for growing file."""
                    while process.returncode is None:
                        try:
                            for item in os.listdir(temp_dir):
                                file_path = os.path.join(temp_dir, item)
                                if os.path.isfile(file_path):
                                    file_size = os.path.getsize(file_path)
                                    if file_size > 0:
                                        # Estimate progress as percentage
                                        # Most audiobooks are 100-500MB, estimate max 500MB
                                        estimated_total = max(file_size, 500 * 1024 * 1024)
                                        progress_percent = min(
                                            100.0, (file_size / estimated_total) * 100
                                        )

                                        await safe_progress_callback(
                                            progress_callback,
                                            event_type="download.progress",
                                            asin=book_asin,
                                            filename=book_title,
                                            progress_percent=progress_percent,
                                            bytes_downloaded=file_size,
                                            total_bytes=estimated_total,
                                            speed_kbps=0.0,
                                        )
                        except Exception as e:
                            logger.debug(f"Error monitoring download: {e}")

                        await asyncio.sleep(1)  # Check every second

                # Start monitoring task
                monitor_task = asyncio.create_task(monitor_download())

                try:
                    stdout, stderr = await process.communicate()
                finally:
                    # Stop monitoring when download completes
                    monitor_task.cancel()
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        pass

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
                    activation_bytes=activation_bytes,
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
