"""Book download functionality."""

import asyncio
import json
import os
import tempfile
import time

from loguru import logger

from ..adapters.storage.minio_storage_adapter import MinIOStorageAdapter
from ..domain.progress import safe_progress_callback
from ..ports.file_storage_port import FileStoragePort
from .decryptor import decrypt_book as decrypt_book_impl


async def download_book(  # noqa: C901
    book: list,
    user_id: str,
    progress_callback=None,
    audible_auth: dict | None = None,
    activation_bytes: str | None = None,
) -> bool:
    """Download a book from Audible using audible-cli and immediately decrypt it.

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

        # Initialize monitor state for cleanup/logging paths.
        last_file_sizes = {}
        progress_emitted = False
        progress_check_count = 0
        iterations = 0

        # Use temporary directory for encrypted file
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"[Download] Using temp directory: {temp_dir}")
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

                async def monitor_download():
                    """Monitor temporary directory for growing file."""
                    nonlocal last_file_sizes, progress_emitted, progress_check_count, iterations

                    logger.warning(
                        f"[Monitor] STARTING monitoring for temp_dir: {temp_dir}"
                    )  # Use warning for visibility

                    while process.returncode is None:
                        iterations += 1
                        progress_check_count += 1
                        try:
                            # Scan all files in temp_dir and subdirectories
                            current_files = {}
                            dir_exists = os.path.isdir(temp_dir)

                            if not dir_exists:
                                logger.warning(f"[Monitor] temp_dir does not exist: {temp_dir}")
                                await asyncio.sleep(0.5)
                                continue

                            for root, dirs, files in os.walk(temp_dir):
                                if files and iterations == 1:
                                    logger.info(f"[Monitor] Found files in {root}: {files}")

                                for file in files:
                                    file_path = os.path.join(root, file)
                                    try:
                                        file_size = os.path.getsize(file_path)
                                        current_files[file_path] = file_size

                                        if file_size > 0:
                                            # Log first detection
                                            if file_path not in last_file_sizes:
                                                logger.info(
                                                    f"[Monitor] Detected file {file} (size: {file_size / 1024 / 1024:.1f}MB)"
                                                )

                                            # Emit progress at 20%, 40%, 60%, 80% intervals
                                            progress_percent = min(
                                                99.0, (file_size / (500 * 1024 * 1024)) * 100
                                            )

                                            # Emit progress at reasonable intervals (every 2.5 seconds = 5 checks at 500ms)
                                            if iterations % 5 == 0:
                                                # Estimate total based on current file size
                                                # Audiobooks typically range 500MB-2GB, so estimate at 1.5x current size
                                                estimated_total = max(
                                                    file_size * 1.5, 1.5 * 1024 * 1024 * 1024
                                                )
                                                progress_percent = (
                                                    file_size / estimated_total
                                                ) * 100

                                                logger.debug(
                                                    f"[Monitor] File size {file_size / 1024 / 1024:.1f}MB, estimated total {estimated_total / 1024 / 1024:.1f}MB -> {progress_percent:.1f}%"
                                                )
                                                await safe_progress_callback(
                                                    progress_callback,
                                                    event_type="download.progress",
                                                    asin=book_asin,
                                                    filename=book_title,
                                                    progress_percent=progress_percent,
                                                    bytes_downloaded=file_size,
                                                    total_bytes=int(estimated_total),
                                                    speed_kbps=0.0,
                                                )
                                                progress_emitted = True
                                    except (OSError, ValueError) as e:
                                        logger.debug(
                                            f"[Monitor] Error reading file {file_path}: {e}"
                                        )

                            last_file_sizes = current_files

                        except Exception as e:
                            logger.warning(f"[Monitor] Error on iteration {iterations}: {e}")

                        await asyncio.sleep(0.5)  # Check every 500ms

                    logger.info(
                        f"[Monitor] Download monitoring completed after {iterations} iterations, "
                        f"progress_emitted={progress_emitted}, final_files={len(last_file_sizes)}"
                    )

                # Start monitoring task
                logger.warning(f"[Download] Creating monitor task for {book_asin}")
                monitor_task = asyncio.create_task(monitor_download())
                logger.warning(f"[Download] Monitor task created: {monitor_task}")
                start_time = time.time()

                try:
                    stdout, stderr = await process.communicate()
                finally:
                    # Stop monitoring when download completes
                    elapsed = time.time() - start_time

                    monitor_task.cancel()
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        pass

                    # Always emit at least one progress event during download
                    # (either from monitoring or as fallback)
                    logger.warning(
                        f"[Download] COMPLETED in {elapsed:.1f}s, "
                        f"progress_emitted={progress_emitted}, monitor_iterations={iterations}, "
                        f"files_found={len(last_file_sizes)}"
                    )

                    if not progress_emitted:
                        # Emit multiple progress updates to show activity
                        logger.warning(f"[Download] Emitting FALLBACK progress for {book_asin}")
                        for idx, progress in enumerate([25, 50, 75, 99]):
                            logger.debug(f"[Download] Fallback progress {idx + 1}/4: {progress}%")
                            await safe_progress_callback(
                                progress_callback,
                                event_type="download.progress",
                                asin=book_asin,
                                filename=book_title,
                                progress_percent=float(progress),
                                bytes_downloaded=0,
                                total_bytes=1,
                                speed_kbps=0.0,
                            )
                            await asyncio.sleep(0.05)  # Small delay between updates

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

                try:
                    final_size = os.path.getsize(downloaded_file_path)
                    await safe_progress_callback(
                        progress_callback,
                        event_type="download.progress",
                        asin=book_asin,
                        filename=book_title,
                        progress_percent=100.0,
                        bytes_downloaded=final_size,
                        total_bytes=final_size,
                        speed_kbps=0.0,
                    )
                except OSError as e:
                    logger.debug(f"[Download] Failed to read final size for {book_asin}: {e}")

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


async def validate_book(
    book: list,
    user_id: str,
    storage: FileStoragePort | None = None,
) -> bool:
    """Validate that a downloaded (encrypted) book exists in MinIO for the user."""
    if not user_id:
        logger.error("user_id is required to validate downloaded book")
        return False

    if not book:
        logger.error("Book data is missing asin for validation")
        return False

    asin = str(book[0])
    if not asin:
        logger.error("Book ASIN missing; cannot validate downloaded file")
        return False

    storage = storage or MinIOStorageAdapter()
    object_key = f"downloaded/{asin}.aax"

    exists = storage.file_exists(user_id, object_key)
    if exists:
        logger.info(f"Validated downloaded file exists: {object_key}")
    else:
        logger.warning(f"Downloaded file not found: {object_key}")
    return exists
