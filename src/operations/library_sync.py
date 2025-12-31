"""Library synchronization workflow using PostgreSQL database.

This module replaces library_sync.py to use database operations instead of CSV.
It provides the same public API but backed by PostgreSQL.
"""

import asyncio
from typing import Optional, Callable, Any, Awaitable

from loguru import logger

from ..core.config import Config
from ..database import user_ops
from .db_manager import get_library_manager
from .decryptor import decrypt_book
from .downloader import download_book


async def get_user(username: str = "user") -> str:
    """Get existing user by username.

    Args:
        username: Username to lookup

    Returns:
        User ID if found, None otherwise
    """
    user = user_ops.get_user_by_username(username)
    if user:
        logger.info(f"Using existing user: {username}")
        return user["user_id"]
    return "User not found"


async def create_user(username: str = "user", email: str = "user@example.com") -> str:
    """Create a new user.

    Args:
        username: Username to use
        email: Email to use

    Returns:
        User ID

    Raises:
        RuntimeError: If user creation fails
    """
    user_id = user_ops.create_user(
        username=username,
        email=email,
        auth_file_path=Config.AUTH_FILE,
        activation_bytes=Config.ACTIVATION_BYTES,
    )

    if user_id:
        logger.info(f"Created new user: {username}")
        return user_id

    raise RuntimeError(f"Failed to create user: {username}")


async def sync_library(
    user_id: Optional[str] = None,
    ws_broadcast_fn: Optional[Callable[..., Awaitable[Any]]] = None,
) -> None:
    """Main synchronization workflow using database.

    This is the entry point for library synchronization.
    It replaces the CSV-based sync_library function.

    Args:
        user_id: User ID to sync for. If None, uses default "user" (CLI mode).
        ws_broadcast_fn: Optional async callable for progress updates.
                        Called with event_type and kwargs.
                        Example: await ws_broadcast_fn(
                            event_type="sync.progress",
                            current_book="B123",
                            books_processed=5,
                            books_total=10
                        )
    """
    try:
        # Ensure all directories exist
        Config.ensure_directories()

        # Get or create user (if not provided, use default)
        if user_id is None:
            user_id = await get_user()

        # Get library manager for this user
        library_manager = await get_library_manager(user_id)

        # Create sync record
        sync_id = await library_manager.create_sync("full")
        if not sync_id:
            logger.error("Failed to create sync record")
            return

        try:
            # Find books to process (missing books)
            missing_books = await library_manager.get_missing_books()
            books_processed = 0

            if missing_books:
                logger.info(f"Processing {len(missing_books)} books...")
                tasks = []

                for book in missing_books:
                    task = asyncio.create_task(
                        process_book(
                            user_id=user_id,
                            book=book,
                            library_manager=library_manager,
                            progress_callback=ws_broadcast_fn,
                        )
                    )
                    tasks.append(task)

                # Process all books concurrently
                await asyncio.gather(*tasks)
                books_processed = len(missing_books)
                logger.info(f"Successfully processed {books_processed} books")
            else:
                logger.info("No books to process.")
                books_processed = 0

            # Complete sync record
            stats = {
                "books_found": len(missing_books),
                "books_added": len(missing_books),
                "books_downloaded": sum(
                    1 for b in missing_books if b.get("is_downloaded")
                ),
                "books_decrypted": sum(
                    1 for b in missing_books if b.get("is_decrypted")
                ),
            }

            await library_manager.complete_sync(
                sync_id=sync_id, status="completed", **stats
            )

            logger.info("Sync completed successfully")

        except Exception as e:
            logger.error(f"Sync operation failed: {e}")
            await library_manager.complete_sync(sync_id, "failed")

    except Exception as e:
        logger.error(f"An error occurred in the sync workflow: {e}")


async def process_book(
    user_id: str,
    book: dict,
    library_manager,
    progress_callback=None,
) -> None:
    """Process a single book: download and decrypt.

    Args:
        user_id: User ID
        book: Book dictionary with ASIN and title
        library_manager: LibraryManager instance
        progress_callback: Optional async callable for progress updates
    """
    asin = book["asin"]
    title = book["title"]

    try:
        logger.info(f"Processing book: {title}")

        # Broadcast download started
        if progress_callback:
            try:
                await progress_callback(
                    event_type="download.started",
                    asin=asin,
                    title=title,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast download.started: {e}")

        # Download book
        download_success = await download_book([asin, title])
        if not download_success:
            raise Exception("Download failed")

        # Broadcast download completed
        if progress_callback:
            try:
                await progress_callback(
                    event_type="download.completed",
                    asin=asin,
                    title=title,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast download.completed: {e}")

        # Broadcast decrypt started
        if progress_callback:
            try:
                await progress_callback(
                    event_type="decrypt.started",
                    asin=asin,
                    title=title,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast decrypt.started: {e}")

        # Decrypt book
        decrypt_success = await decrypt_book([asin, title])
        if not decrypt_success:
            raise Exception("Decryption failed")

        # Broadcast decrypt completed
        if progress_callback:
            try:
                await progress_callback(
                    event_type="decrypt.completed",
                    asin=asin,
                    title=title,
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast decrypt.completed: {e}")

        logger.info(f"Successfully processed: {title}")

    except Exception as e:
        logger.error(f"Processing failed for {title}: {e}")

        # Broadcast error event
        if progress_callback:
            try:
                await progress_callback(
                    event_type="sync.error",
                    asin=asin,
                    title=title,
                    error=str(e),
                )
            except Exception as cb_err:
                logger.warning(f"Failed to broadcast error event: {cb_err}")

        await library_manager.log_error(
            error_type="sync_error",
            error_message=f"Failed to process book: {str(e)}",
            asin=asin,
            severity="error",
        )
