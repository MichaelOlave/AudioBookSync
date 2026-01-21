"""Library synchronization workflow using PostgreSQL database with async ORM.

This module provides database operations using async ORM services.
It provides the same public API but backed by SQLAlchemy ORM.
"""

import asyncio
from typing import Any, Awaitable, Callable, Optional

from loguru import logger

from ..core.config import Config
from ..database.engine import AsyncSessionLocal
from ..database.services import user_service
from .db_manager import get_library_manager
from .handlers import book_processor


async def get_user(username: str = "user") -> str:
    """Get existing user by username using async ORM.

    Args:
        username: Username to lookup

    Returns:
        User ID if found, None otherwise
    """
    async with AsyncSessionLocal() as db:
        user = await user_service.get_user_by_username(db, username)
        if user:
            logger.info(f"Using existing user: {username}")
            return str(user.user_id)
    return "User not found"


async def create_user(username: str = "user", email: str = "user@example.com") -> str:
    """Create a new user using async ORM.

    Args:
        username: Username to use
        email: Email to use

    Returns:
        User ID

    Raises:
        RuntimeError: If user creation fails
    """
    async with AsyncSessionLocal() as db:
        user = await user_service.create_user(
            db=db,
            username=username,
            email=email,
            auth_file_path=Config.AUTH_FILE,
            activation_bytes=Config.ACTIVATION_BYTES,
        )
        await db.commit()

        if user:
            user_id = str(user.user_id)
            logger.info(f"Created new user: {username}")
            return user_id

    raise RuntimeError(f"Failed to create user: {username}")


async def get_or_create_user(username: str = "user", email: str = "user@example.com") -> str:
    """Get existing user or create new one.

    Args:
        username: Username to lookup or create
        email: Email to use for new user

    Returns:
        User ID

    Raises:
        RuntimeError: If user creation fails
    """
    async with AsyncSessionLocal() as db:
        user = await user_service.get_user_by_username(db, username)
        if user:
            logger.info(f"Using existing user: {username}")
            return str(user.user_id)

        user = await user_service.create_user(
            db=db,
            username=username,
            email=email,
            auth_file_path=Config.AUTH_FILE,
            activation_bytes=Config.ACTIVATION_BYTES,
        )
        await db.commit()

        if user:
            user_id = str(user.user_id)
            logger.info(f"Created new user: {username}")
            return user_id

    raise RuntimeError(f"Failed to create user: {username}")


async def sync_library(
    user_id: Optional[str] = None,
    ws_broadcast_fn: Optional[Callable[..., Awaitable[Any]]] = None,
) -> None:
    """Main synchronization workflow using async ORM.

    This is the entry point for library synchronization.
    It uses async ORM services for all database operations.

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
    # Create async database session for the entire sync operation
    async with AsyncSessionLocal() as db:
        try:
            # Ensure all directories exist
            Config.ensure_directories()

            # Get or create user (if not provided, use default)
            if user_id is None:
                user_id = await get_user()

            # Get library manager for this user with database session
            library_manager = await get_library_manager(db, user_id)

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
                    "books_downloaded": sum(1 for b in missing_books if b.get("is_downloaded")),
                    "books_decrypted": sum(1 for b in missing_books if b.get("is_decrypted")),
                }

                await library_manager.complete_sync(sync_id=sync_id, status="completed", **stats)

                logger.info("Sync completed successfully")
                await db.commit()

            except Exception as e:
                logger.error(f"Sync operation failed: {e}")
                await library_manager.complete_sync(sync_id, "failed")
                await db.commit()

        except Exception as e:
            logger.error(f"An error occurred in the sync workflow: {e}")
            await db.rollback()


async def process_book(
    user_id: str,
    book: dict,
    library_manager,
    progress_callback=None,
) -> None:
    """Process a single book: download and decrypt.

    Delegates to BookProcessingHandler for orchestration of the
    download and decrypt workflow with progress tracking.

    Args:
        user_id: User ID
        book: Book dictionary with ASIN and title
        library_manager: LibraryManager instance
        progress_callback: Optional async callable for progress updates
    """
    await book_processor.process_book(
        user_id=user_id,
        book=book,
        library_manager=library_manager,
        progress_callback=progress_callback,
    )
