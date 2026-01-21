"""Sync history database service layer using SQLAlchemy ORM."""

from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database.models.sync import SyncHistory


async def create_sync_history(
    db: AsyncSession,
    user_id: UUID,
    sync_type: str = "full",
    notes: Optional[str] = None,
) -> Optional[SyncHistory]:
    """
    Create a new sync history record.

    Args:
        db: Database session
        user_id: User UUID
        sync_type: Type of sync (full, incremental, manual)
        notes: Optional notes about the sync

    Returns:
        SyncHistory object if successful, None otherwise
    """
    try:
        sync = SyncHistory(
            user_id=user_id,
            sync_type=sync_type,
            status="in_progress",
            notes=notes,
        )
        db.add(sync)
        await db.flush()
        await db.refresh(sync)
        logger.info(f"Created sync history: {user_id} ({sync_type}) (ID: {sync.sync_id})")
        return sync
    except Exception as e:
        logger.error(f"Failed to create sync history: {e}")
        return None


async def get_sync_by_id(db: AsyncSession, sync_id: UUID) -> Optional[SyncHistory]:
    """
    Get sync history by ID.

    Args:
        db: Database session
        sync_id: Sync UUID

    Returns:
        SyncHistory object if found, None otherwise
    """
    try:
        result = await db.execute(
            select(SyncHistory).where(SyncHistory.sync_id == sync_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get sync history: {e}")
        return None


async def get_syncs_by_user(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 50,
) -> List[SyncHistory]:
    """
    Get sync history for a user.

    Args:
        db: Database session
        user_id: User UUID
        limit: Maximum number of records to return

    Returns:
        List of SyncHistory objects
    """
    try:
        result = await db.execute(
            select(SyncHistory)
            .where(SyncHistory.user_id == user_id)
            .order_by(SyncHistory.sync_started_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get syncs for user: {e}")
        return []


async def get_latest_sync(db: AsyncSession, user_id: UUID) -> Optional[SyncHistory]:
    """
    Get the latest sync for a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        Latest SyncHistory object if found, None otherwise
    """
    try:
        result = await db.execute(
            select(SyncHistory)
            .where(SyncHistory.user_id == user_id)
            .order_by(SyncHistory.sync_started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get latest sync: {e}")
        return None


async def update_sync_status(
    db: AsyncSession,
    sync_id: UUID,
    status: str,
    books_found: Optional[int] = None,
    books_added: Optional[int] = None,
    books_removed: Optional[int] = None,
    books_downloaded: Optional[int] = None,
    books_decrypted: Optional[int] = None,
    errors_count: Optional[int] = None,
    notes: Optional[str] = None,
) -> bool:
    """
    Update sync status with statistics.

    Args:
        db: Database session
        sync_id: Sync UUID
        status: New status (in_progress, completed, partial, failed, cancelled)
        books_found: Number of books found
        books_added: Number of books added
        books_removed: Number of books removed
        books_downloaded: Number of books downloaded
        books_decrypted: Number of books decrypted
        errors_count: Number of errors
        notes: Additional notes

    Returns:
        True if successful, False otherwise
    """
    try:
        sync = await get_sync_by_id(db, sync_id)
        if not sync:
            return False

        sync.status = status
        if books_found is not None:
            sync.books_found = books_found
        if books_added is not None:
            sync.books_added = books_added
        if books_removed is not None:
            sync.books_removed = books_removed
        if books_downloaded is not None:
            sync.books_downloaded = books_downloaded
        if books_decrypted is not None:
            sync.books_decrypted = books_decrypted
        if errors_count is not None:
            sync.errors_count = errors_count
        if notes is not None:
            sync.notes = notes

        # Mark as completed if appropriate
        if status in ["completed", "partial", "failed", "cancelled"]:
            sync.sync_completed_at = datetime.now(timezone.utc)
            if sync.sync_started_at:
                duration = (sync.sync_completed_at - sync.sync_started_at).total_seconds()
                sync.duration_seconds = int(duration)

        await db.flush()
        logger.info(f"Updated sync status: {sync_id} -> {status}")
        return True
    except Exception as e:
        logger.error(f"Failed to update sync status: {e}")
        return False


async def complete_sync(
    db: AsyncSession,
    sync_id: UUID,
    books_found: int,
    books_added: int,
    books_removed: int,
    books_downloaded: int,
    books_decrypted: int,
    errors_count: int = 0,
) -> bool:
    """
    Mark a sync as completed with final statistics.

    Args:
        db: Database session
        sync_id: Sync UUID
        books_found: Number of books found
        books_added: Number of books added
        books_removed: Number of books removed
        books_downloaded: Number of books downloaded
        books_decrypted: Number of books decrypted
        errors_count: Number of errors

    Returns:
        True if successful, False otherwise
    """
    try:
        sync = await get_sync_by_id(db, sync_id)
        if not sync:
            return False

        sync.status = "completed"
        sync.books_found = books_found
        sync.books_added = books_added
        sync.books_removed = books_removed
        sync.books_downloaded = books_downloaded
        sync.books_decrypted = books_decrypted
        sync.errors_count = errors_count
        sync.sync_completed_at = datetime.now(timezone.utc)

        if sync.sync_started_at:
            duration = (sync.sync_completed_at - sync.sync_started_at).total_seconds()
            sync.duration_seconds = int(duration)

        await db.flush()
        logger.info(f"Completed sync: {sync_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to complete sync: {e}")
        return False


async def fail_sync(
    db: AsyncSession,
    sync_id: UUID,
    error_message: str,
    books_found: int = 0,
    books_added: int = 0,
    errors_count: int = 1,
) -> bool:
    """
    Mark a sync as failed.

    Args:
        db: Database session
        sync_id: Sync UUID
        error_message: Error message
        books_found: Number of books found before failure
        books_added: Number of books added before failure
        errors_count: Number of errors encountered

    Returns:
        True if successful, False otherwise
    """
    try:
        sync = await get_sync_by_id(db, sync_id)
        if not sync:
            return False

        sync.status = "failed"
        sync.books_found = books_found
        sync.books_added = books_added
        sync.errors_count = errors_count
        sync.notes = error_message
        sync.sync_completed_at = datetime.now(timezone.utc)

        if sync.sync_started_at:
            duration = (sync.sync_completed_at - sync.sync_started_at).total_seconds()
            sync.duration_seconds = int(duration)

        await db.flush()
        logger.info(f"Failed sync: {sync_id} - {error_message}")
        return True
    except Exception as e:
        logger.error(f"Failed to mark sync as failed: {e}")
        return False


async def get_incomplete_syncs(db: AsyncSession) -> List[SyncHistory]:
    """
    Get all incomplete syncs (for cleanup/recovery).

    Args:
        db: Database session

    Returns:
        List of incomplete SyncHistory objects
    """
    try:
        result = await db.execute(
            select(SyncHistory)
            .where(SyncHistory.status == "in_progress")
            .order_by(SyncHistory.sync_started_at)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get incomplete syncs: {e}")
        return []


async def get_failed_syncs(db: AsyncSession, limit: int = 50) -> List[SyncHistory]:
    """
    Get failed syncs for analysis.

    Args:
        db: Database session
        limit: Maximum number of records to return

    Returns:
        List of failed SyncHistory objects
    """
    try:
        result = await db.execute(
            select(SyncHistory)
            .where(SyncHistory.status == "failed")
            .order_by(SyncHistory.sync_started_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get failed syncs: {e}")
        return []


async def get_sync_statistics(
    db: AsyncSession,
    user_id: UUID,
) -> Optional[dict]:
    """
    Get aggregated sync statistics for a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        Dictionary with aggregated statistics
    """
    try:
        syncs = await get_syncs_by_user(db, user_id, limit=None)
        if not syncs:
            return None

        total_syncs = len(syncs)
        completed = sum(1 for s in syncs if s.status == "completed")
        failed = sum(1 for s in syncs if s.status == "failed")
        total_books_added = sum(s.books_added or 0 for s in syncs)
        total_books_downloaded = sum(s.books_downloaded or 0 for s in syncs)
        total_books_decrypted = sum(s.books_decrypted or 0 for s in syncs)
        total_errors = sum(s.errors_count or 0 for s in syncs)

        return {
            "total_syncs": total_syncs,
            "completed": completed,
            "failed": failed,
            "total_books_added": total_books_added,
            "total_books_downloaded": total_books_downloaded,
            "total_books_decrypted": total_books_decrypted,
            "total_errors": total_errors,
            "success_rate": completed / total_syncs if total_syncs > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Failed to get sync statistics: {e}")
        return None


async def delete_sync(db: AsyncSession, sync_id: UUID) -> bool:
    """
    Delete a sync record.

    Args:
        db: Database session
        sync_id: Sync UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        sync = await get_sync_by_id(db, sync_id)
        if not sync:
            return False

        await db.delete(sync)
        await db.flush()
        logger.info(f"Deleted sync: {sync_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete sync: {e}")
        return False
