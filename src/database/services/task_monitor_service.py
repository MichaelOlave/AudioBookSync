"""Task monitoring service for active downloads, decryptions, and syncs."""

from typing import Dict, List, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.book import Book
from src.database.models.decryption import DecryptionStatus
from src.database.models.download import DownloadStatus
from src.database.models.sync import SyncHistory


async def get_active_tasks_by_user(db: AsyncSession, user_id: str) -> Dict[str, List[Dict]]:
    """
    Get all active tasks for a user across all operation types.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dict with keys 'downloads', 'decryptions', 'syncs' containing task data
    """

    # Query active downloads (status = 'downloading')
    downloads_query = (
        select(DownloadStatus, Book.title)
        .join(Book, DownloadStatus.asin == Book.asin)
        .where(
            and_(
                Book.user_id == UUID(user_id),
                DownloadStatus.status == "downloading",
            )
        )
        .order_by(DownloadStatus.download_started_at.desc())
    )

    downloads_result = await db.execute(downloads_query)
    downloads_data = []
    for row in downloads_result:
        download, title = row
        downloads_data.append(
            {
                "task_id": str(download.download_id),
                "asin": download.asin,
                "title": title,
                "status": download.status,
                "started_at": download.download_started_at,
                "attempt_number": download.attempt_number,
                "error_message": download.error_message,
            }
        )

    # Query active decryptions (status = 'decrypting')
    decryptions_query = (
        select(DecryptionStatus, Book.title)
        .join(Book, DecryptionStatus.asin == Book.asin)
        .where(
            and_(
                Book.user_id == UUID(user_id),
                DecryptionStatus.status == "decrypting",
            )
        )
        .order_by(DecryptionStatus.decryption_started_at.desc())
    )

    decryptions_result = await db.execute(decryptions_query)
    decryptions_data = []
    for row in decryptions_result:
        decryption, title = row
        decryptions_data.append(
            {
                "task_id": str(decryption.decryption_id),
                "asin": decryption.asin,
                "title": title,
                "status": decryption.status,
                "started_at": decryption.decryption_started_at,
                "error_message": decryption.error_message,
            }
        )

    # Query active syncs (status = 'in_progress')
    syncs_query = (
        select(SyncHistory)
        .where(
            and_(
                SyncHistory.user_id == UUID(user_id),
                SyncHistory.status == "in_progress",
            )
        )
        .order_by(SyncHistory.sync_started_at.desc())
    )

    syncs_result = await db.execute(syncs_query)
    syncs_data = []
    for row in syncs_result:
        sync = row[0]
        syncs_data.append(
            {
                "task_id": str(sync.sync_id),
                "status": sync.status,
                "started_at": sync.sync_started_at,
                "sync_type": sync.sync_type,
                "books_found": sync.books_found,
                "books_added": sync.books_added,
            }
        )

    return {
        "downloads": downloads_data,
        "decryptions": decryptions_data,
        "syncs": syncs_data,
    }


async def cancel_task(
    db: AsyncSession,
    task_id: UUID,
    user_id: str,
) -> Tuple[bool, str, str, str]:
    """
    Cancel a task by ID.

    Args:
        db: Database session
        task_id: Task UUID
        user_id: User ID for authorization

    Returns:
        Tuple of (success, task_type, current_status, message)

    Raises:
        ValueError: If task not found or not authorized
    """

    # Try to find in downloads
    download_query = (
        select(DownloadStatus)
        .join(Book, DownloadStatus.asin == Book.asin)
        .where(
            and_(
                DownloadStatus.download_id == task_id,
                Book.user_id == UUID(user_id),
            )
        )
    )
    result = await db.execute(download_query)
    download = result.scalar_one_or_none()

    if download:
        if download.status in ["completed", "failed", "cancelled"]:
            return (
                False,
                "download",
                download.status,
                f"Task already {download.status}",
            )

        download.status = "cancelled"
        await db.commit()
        logger.info(f"Cancelled download task {task_id}")
        return True, "download", "cancelled", "Task cancelled successfully"

    # Try to find in decryptions
    decryption_query = (
        select(DecryptionStatus)
        .join(Book, DecryptionStatus.asin == Book.asin)
        .where(
            and_(
                DecryptionStatus.decryption_id == task_id,
                Book.user_id == UUID(user_id),
            )
        )
    )
    result = await db.execute(decryption_query)
    decryption = result.scalar_one_or_none()

    if decryption:
        if decryption.status in ["completed", "failed", "cancelled"]:
            return (
                False,
                "decryption",
                decryption.status,
                f"Task already {decryption.status}",
            )

        decryption.status = "cancelled"
        await db.commit()
        logger.info(f"Cancelled decryption task {task_id}")
        return True, "decryption", "cancelled", "Task cancelled successfully"

    # Try to find in syncs
    sync_query = select(SyncHistory).where(
        and_(
            SyncHistory.sync_id == task_id,
            SyncHistory.user_id == UUID(user_id),
        )
    )
    result = await db.execute(sync_query)
    sync = result.scalar_one_or_none()

    if sync:
        if sync.status in ["completed", "failed", "cancelled"]:
            return (
                False,
                "sync",
                sync.status,
                f"Task already {sync.status}",
            )

        sync.status = "cancelled"
        await db.commit()
        logger.info(f"Cancelled sync task {task_id}")
        return True, "sync", "cancelled", "Task cancelled successfully"

    # Task not found
    raise ValueError(f"Task {task_id} not found or not authorized")
