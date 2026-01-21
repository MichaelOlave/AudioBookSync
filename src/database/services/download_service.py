"""Download status database service layer using SQLAlchemy ORM."""

from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from loguru import logger

from src.database.models.download import DownloadStatus
from src.database.models.book import Book


async def create_download_status(
    db: AsyncSession,
    asin: str,
    status: str = "pending",
    download_path: Optional[str] = None,
    attempt_number: int = 1,
) -> Optional[DownloadStatus]:
    """
    Create a new download status record.

    Args:
        db: Database session
        asin: Book ASIN
        status: Download status (pending, downloading, completed, failed, cancelled)
        download_path: Path to download file
        attempt_number: Download attempt number

    Returns:
        DownloadStatus object if successful, None otherwise
    """
    try:
        download = DownloadStatus(
            asin=asin,
            status=status,
            download_path=download_path,
            attempt_number=attempt_number,
        )
        db.add(download)
        await db.flush()
        await db.refresh(download)
        logger.info(f"Created download status: {asin} (ID: {download.download_id})")
        return download
    except Exception as e:
        logger.error(f"Failed to create download status: {e}")
        return None


async def get_download_by_id(db: AsyncSession, download_id: UUID) -> Optional[DownloadStatus]:
    """
    Get download status by ID.

    Args:
        db: Database session
        download_id: Download UUID

    Returns:
        DownloadStatus object if found, None otherwise
    """
    try:
        result = await db.execute(
            select(DownloadStatus).where(DownloadStatus.download_id == download_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get download status: {e}")
        return None


async def get_downloads_by_asin(db: AsyncSession, asin: str) -> List[DownloadStatus]:
    """
    Get all download records for a book.

    Args:
        db: Database session
        asin: Book ASIN

    Returns:
        List of DownloadStatus objects
    """
    try:
        result = await db.execute(
            select(DownloadStatus)
            .where(DownloadStatus.asin == asin)
            .order_by(DownloadStatus.created_at.desc())
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get downloads for ASIN: {e}")
        return []


async def get_latest_download(db: AsyncSession, asin: str) -> Optional[DownloadStatus]:
    """
    Get the latest download record for a book.

    Args:
        db: Database session
        asin: Book ASIN

    Returns:
        Latest DownloadStatus object if found, None otherwise
    """
    try:
        result = await db.execute(
            select(DownloadStatus)
            .where(DownloadStatus.asin == asin)
            .order_by(DownloadStatus.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get latest download: {e}")
        return None


async def update_download_status(
    db: AsyncSession,
    download_id: UUID,
    status: str,
    download_path: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    error_message: Optional[str] = None,
    error_details: Optional[dict] = None,
) -> bool:
    """
    Update download status.

    Args:
        db: Database session
        download_id: Download UUID
        status: New status
        download_path: Path to downloaded file
        file_size_bytes: Size of downloaded file
        error_message: Error message if failed
        error_details: Detailed error info

    Returns:
        True if successful, False otherwise
    """
    try:
        download = await get_download_by_id(db, download_id)
        if not download:
            return False

        download.status = status
        if download_path:
            download.download_path = download_path
        if file_size_bytes:
            download.file_size_bytes = file_size_bytes
        if error_message:
            download.error_message = error_message
        if error_details:
            download.error_details = error_details

        # Set timestamps based on status
        now = datetime.now(timezone.utc)
        if status == "downloading":
            download.download_started_at = now
        elif status == "completed":
            download.download_completed_at = now
        elif status == "failed":
            download.download_completed_at = now

        await db.flush()
        logger.info(f"Updated download status: {download_id} -> {status}")
        return True
    except Exception as e:
        logger.error(f"Failed to update download status: {e}")
        return False


async def start_download(db: AsyncSession, download_id: UUID) -> bool:
    """
    Mark a download as started.

    Args:
        db: Database session
        download_id: Download UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        download = await get_download_by_id(db, download_id)
        if not download:
            return False

        download.status = "downloading"
        download.download_started_at = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"Started download: {download_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to start download: {e}")
        return False


async def complete_download(
    db: AsyncSession,
    download_id: UUID,
    download_path: str,
    file_size_bytes: int,
) -> bool:
    """
    Mark a download as completed.

    Args:
        db: Database session
        download_id: Download UUID
        download_path: Path to downloaded file
        file_size_bytes: Size of file in bytes

    Returns:
        True if successful, False otherwise
    """
    try:
        download = await get_download_by_id(db, download_id)
        if not download:
            return False

        download.status = "completed"
        download.download_path = download_path
        download.file_size_bytes = file_size_bytes
        download.download_completed_at = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"Completed download: {download_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to complete download: {e}")
        return False


async def fail_download(
    db: AsyncSession,
    download_id: UUID,
    error_message: str,
    error_details: Optional[dict] = None,
    attempt_number: Optional[int] = None,
) -> bool:
    """
    Mark a download as failed.

    Args:
        db: Database session
        download_id: Download UUID
        error_message: Error message
        error_details: Detailed error info
        attempt_number: Increment attempt counter if provided

    Returns:
        True if successful, False otherwise
    """
    try:
        download = await get_download_by_id(db, download_id)
        if not download:
            return False

        download.status = "failed"
        download.error_message = error_message
        if error_details:
            download.error_details = error_details
        if attempt_number:
            download.attempt_number = attempt_number
        download.download_completed_at = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"Failed download: {download_id} - {error_message}")
        return True
    except Exception as e:
        logger.error(f"Failed to mark download as failed: {e}")
        return False


async def get_pending_downloads(db: AsyncSession) -> List[DownloadStatus]:
    """
    Get all pending downloads.

    Args:
        db: Database session

    Returns:
        List of pending DownloadStatus objects
    """
    try:
        result = await db.execute(
            select(DownloadStatus)
            .where(DownloadStatus.status == "pending")
            .order_by(DownloadStatus.created_at)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get pending downloads: {e}")
        return []


async def get_failed_downloads(db: AsyncSession, limit: int = 100) -> List[DownloadStatus]:
    """
    Get failed downloads for retry analysis.

    Args:
        db: Database session
        limit: Maximum number of records to return

    Returns:
        List of failed DownloadStatus objects
    """
    try:
        result = await db.execute(
            select(DownloadStatus)
            .where(DownloadStatus.status == "failed")
            .order_by(DownloadStatus.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get failed downloads: {e}")
        return []


async def delete_download(db: AsyncSession, download_id: UUID) -> bool:
    """
    Delete a download record.

    Args:
        db: Database session
        download_id: Download UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        download = await get_download_by_id(db, download_id)
        if not download:
            return False

        await db.delete(download)
        await db.flush()
        logger.info(f"Deleted download: {download_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete download: {e}")
        return False


async def get_downloads_by_user(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[DownloadStatus]:
    """
    Get downloads for a specific user with optional status filter.

    Args:
        db: Database session
        user_id: User UUID
        status: Optional status filter (pending, downloading, completed, failed, cancelled)
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        List of DownloadStatus objects
    """
    try:
        query = select(DownloadStatus).join(
            Book, DownloadStatus.asin == Book.asin
        ).where(
            Book.user_id == user_id
        )

        if status:
            query = query.where(DownloadStatus.status == status)

        query = query.order_by(
            DownloadStatus.created_at.desc()
        ).limit(limit).offset(offset)

        result = await db.execute(query)
        downloads = result.scalars().all()
        logger.info(f"Retrieved {len(downloads)} downloads for user {user_id}")
        return downloads
    except Exception as e:
        logger.error(f"Failed to get downloads for user {user_id}: {e}")
        return []


async def count_downloads_by_user(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
) -> int:
    """
    Count downloads for a specific user with optional status filter.

    Args:
        db: Database session
        user_id: User UUID
        status: Optional status filter (pending, downloading, completed, failed, cancelled)

    Returns:
        Total count of downloads
    """
    try:
        query = select(func.count(DownloadStatus.download_id)).join(
            Book, DownloadStatus.asin == Book.asin
        ).where(
            Book.user_id == user_id
        )

        if status:
            query = query.where(DownloadStatus.status == status)

        result = await db.execute(query)
        count = result.scalar_one_or_none() or 0
        logger.info(f"Counted {count} downloads for user {user_id}")
        return count
    except Exception as e:
        logger.error(f"Failed to count downloads for user {user_id}: {e}")
        return 0


async def get_download_by_id_for_user(
    db: AsyncSession,
    download_id: UUID,
    user_id: str,
) -> Optional[DownloadStatus]:
    """
    Get download status by ID and verify user ownership.

    Args:
        db: Database session
        download_id: Download UUID
        user_id: User UUID to verify ownership

    Returns:
        DownloadStatus object if found and user owns it, None otherwise
    """
    try:
        result = await db.execute(
            select(DownloadStatus)
            .join(Book, DownloadStatus.asin == Book.asin)
            .where(
                and_(
                    DownloadStatus.download_id == download_id,
                    Book.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get download by ID for user {user_id}: {e}")
        return None
