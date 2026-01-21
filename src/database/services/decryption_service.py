"""Decryption status database service layer using SQLAlchemy ORM."""

from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from loguru import logger

from src.database.models.decryption import DecryptionStatus
from src.database.models.book import Book


async def create_decryption_status(
    db: AsyncSession,
    asin: str,
    download_id: Optional[UUID] = None,
    status: str = "pending",
    input_path: Optional[str] = None,
    output_format: str = "m4b",
) -> Optional[DecryptionStatus]:
    """
    Create a new decryption status record.

    Args:
        db: Database session
        asin: Book ASIN
        download_id: Related download ID
        status: Decryption status (pending, decrypting, completed, failed, cancelled)
        input_path: Path to encrypted file
        output_format: Output audio format (m4b, mp3, flac, aac)

    Returns:
        DecryptionStatus object if successful, None otherwise
    """
    try:
        decryption = DecryptionStatus(
            asin=asin,
            download_id=download_id,
            status=status,
            input_path=input_path,
            output_format=output_format,
        )
        db.add(decryption)
        await db.flush()
        await db.refresh(decryption)
        logger.info(f"Created decryption status: {asin} (ID: {decryption.decryption_id})")
        return decryption
    except Exception as e:
        logger.error(f"Failed to create decryption status: {e}")
        return None


async def get_decryption_by_id(db: AsyncSession, decryption_id: UUID) -> Optional[DecryptionStatus]:
    """
    Get decryption status by ID.

    Args:
        db: Database session
        decryption_id: Decryption UUID

    Returns:
        DecryptionStatus object if found, None otherwise
    """
    try:
        result = await db.execute(
            select(DecryptionStatus).where(DecryptionStatus.decryption_id == decryption_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get decryption status: {e}")
        return None


async def get_decryptions_by_asin(db: AsyncSession, asin: str) -> List[DecryptionStatus]:
    """
    Get all decryption records for a book.

    Args:
        db: Database session
        asin: Book ASIN

    Returns:
        List of DecryptionStatus objects
    """
    try:
        result = await db.execute(
            select(DecryptionStatus)
            .where(DecryptionStatus.asin == asin)
            .order_by(DecryptionStatus.created_at.desc())
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get decryptions for ASIN: {e}")
        return []


async def get_latest_decryption(db: AsyncSession, asin: str) -> Optional[DecryptionStatus]:
    """
    Get the latest decryption record for a book.

    Args:
        db: Database session
        asin: Book ASIN

    Returns:
        Latest DecryptionStatus object if found, None otherwise
    """
    try:
        result = await db.execute(
            select(DecryptionStatus)
            .where(DecryptionStatus.asin == asin)
            .order_by(DecryptionStatus.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get latest decryption: {e}")
        return None


async def update_decryption_status(
    db: AsyncSession,
    decryption_id: UUID,
    status: str,
    output_path: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    error_message: Optional[str] = None,
    error_details: Optional[dict] = None,
) -> bool:
    """
    Update decryption status.

    Args:
        db: Database session
        decryption_id: Decryption UUID
        status: New status
        output_path: Path to decrypted file
        duration_seconds: Duration of audio in seconds
        error_message: Error message if failed
        error_details: Detailed error info

    Returns:
        True if successful, False otherwise
    """
    try:
        decryption = await get_decryption_by_id(db, decryption_id)
        if not decryption:
            return False

        decryption.status = status
        if output_path:
            decryption.output_path = output_path
        if duration_seconds:
            decryption.duration_seconds = duration_seconds
        if error_message:
            decryption.error_message = error_message
        if error_details:
            decryption.error_details = error_details

        # Set timestamps based on status
        now = datetime.now(timezone.utc)
        if status == "decrypting":
            decryption.decryption_started_at = now
        elif status == "completed":
            decryption.decryption_completed_at = now
        elif status == "failed":
            decryption.decryption_completed_at = now

        await db.flush()
        logger.info(f"Updated decryption status: {decryption_id} -> {status}")
        return True
    except Exception as e:
        logger.error(f"Failed to update decryption status: {e}")
        return False


async def start_decryption(db: AsyncSession, decryption_id: UUID, input_path: str) -> bool:
    """
    Mark a decryption as started.

    Args:
        db: Database session
        decryption_id: Decryption UUID
        input_path: Path to encrypted file

    Returns:
        True if successful, False otherwise
    """
    try:
        decryption = await get_decryption_by_id(db, decryption_id)
        if not decryption:
            return False

        decryption.status = "decrypting"
        decryption.input_path = input_path
        decryption.decryption_started_at = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"Started decryption: {decryption_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to start decryption: {e}")
        return False


async def complete_decryption(
    db: AsyncSession,
    decryption_id: UUID,
    output_path: str,
    duration_seconds: Optional[int] = None,
) -> bool:
    """
    Mark a decryption as completed.

    Args:
        db: Database session
        decryption_id: Decryption UUID
        output_path: Path to decrypted file
        duration_seconds: Duration of audio in seconds

    Returns:
        True if successful, False otherwise
    """
    try:
        decryption = await get_decryption_by_id(db, decryption_id)
        if not decryption:
            return False

        decryption.status = "completed"
        decryption.output_path = output_path
        if duration_seconds:
            decryption.duration_seconds = duration_seconds
        decryption.decryption_completed_at = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"Completed decryption: {decryption_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to complete decryption: {e}")
        return False


async def fail_decryption(
    db: AsyncSession,
    decryption_id: UUID,
    error_message: str,
    error_details: Optional[dict] = None,
) -> bool:
    """
    Mark a decryption as failed.

    Args:
        db: Database session
        decryption_id: Decryption UUID
        error_message: Error message
        error_details: Detailed error info

    Returns:
        True if successful, False otherwise
    """
    try:
        decryption = await get_decryption_by_id(db, decryption_id)
        if not decryption:
            return False

        decryption.status = "failed"
        decryption.error_message = error_message
        if error_details:
            decryption.error_details = error_details
        decryption.decryption_completed_at = datetime.now(timezone.utc)
        await db.flush()
        logger.info(f"Failed decryption: {decryption_id} - {error_message}")
        return True
    except Exception as e:
        logger.error(f"Failed to mark decryption as failed: {e}")
        return False


async def get_pending_decryptions(db: AsyncSession) -> List[DecryptionStatus]:
    """
    Get all pending decryptions.

    Args:
        db: Database session

    Returns:
        List of pending DecryptionStatus objects
    """
    try:
        result = await db.execute(
            select(DecryptionStatus)
            .where(DecryptionStatus.status == "pending")
            .order_by(DecryptionStatus.created_at)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get pending decryptions: {e}")
        return []


async def get_failed_decryptions(db: AsyncSession, limit: int = 100) -> List[DecryptionStatus]:
    """
    Get failed decryptions for retry analysis.

    Args:
        db: Database session
        limit: Maximum number of records to return

    Returns:
        List of failed DecryptionStatus objects
    """
    try:
        result = await db.execute(
            select(DecryptionStatus)
            .where(DecryptionStatus.status == "failed")
            .order_by(DecryptionStatus.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get failed decryptions: {e}")
        return []


async def delete_decryption(db: AsyncSession, decryption_id: UUID) -> bool:
    """
    Delete a decryption record.

    Args:
        db: Database session
        decryption_id: Decryption UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        decryption = await get_decryption_by_id(db, decryption_id)
        if not decryption:
            return False

        await db.delete(decryption)
        await db.flush()
        logger.info(f"Deleted decryption: {decryption_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete decryption: {e}")
        return False


async def get_decryptions_by_user(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[DecryptionStatus]:
    """
    Get decryptions for a specific user with optional status filter.

    Args:
        db: Database session
        user_id: User UUID
        status: Optional status filter (pending, decrypting, completed, failed, cancelled)
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        List of DecryptionStatus objects
    """
    try:
        query = select(DecryptionStatus).join(
            Book, DecryptionStatus.asin == Book.asin
        ).where(
            Book.user_id == user_id
        )

        if status:
            query = query.where(DecryptionStatus.status == status)

        query = query.order_by(
            DecryptionStatus.created_at.desc()
        ).limit(limit).offset(offset)

        result = await db.execute(query)
        decryptions = result.scalars().all()
        logger.info(f"Retrieved {len(decryptions)} decryptions for user {user_id}")
        return decryptions
    except Exception as e:
        logger.error(f"Failed to get decryptions for user {user_id}: {e}")
        return []


async def count_decryptions_by_user(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
) -> int:
    """
    Count decryptions for a specific user with optional status filter.

    Args:
        db: Database session
        user_id: User UUID
        status: Optional status filter (pending, decrypting, completed, failed, cancelled)

    Returns:
        Total count of decryptions
    """
    try:
        query = select(func.count(DecryptionStatus.decryption_id)).join(
            Book, DecryptionStatus.asin == Book.asin
        ).where(
            Book.user_id == user_id
        )

        if status:
            query = query.where(DecryptionStatus.status == status)

        result = await db.execute(query)
        count = result.scalar_one_or_none() or 0
        logger.info(f"Counted {count} decryptions for user {user_id}")
        return count
    except Exception as e:
        logger.error(f"Failed to count decryptions for user {user_id}: {e}")
        return 0


async def get_decryption_by_id_for_user(
    db: AsyncSession,
    decryption_id: UUID,
    user_id: str,
) -> Optional[DecryptionStatus]:
    """
    Get decryption status by ID and verify user ownership.

    Args:
        db: Database session
        decryption_id: Decryption UUID
        user_id: User UUID to verify ownership

    Returns:
        DecryptionStatus object if found and user owns it, None otherwise
    """
    try:
        result = await db.execute(
            select(DecryptionStatus)
            .join(Book, DecryptionStatus.asin == Book.asin)
            .where(
                and_(
                    DecryptionStatus.decryption_id == decryption_id,
                    Book.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get decryption by ID for user {user_id}: {e}")
        return None
