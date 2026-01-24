"""Error logging database service layer using SQLAlchemy ORM."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.error import ErrorLog


async def log_error(
    db: AsyncSession,
    error_type: str,
    error_message: str,
    error_code: Optional[str] = None,
    user_id: Optional[UUID] = None,
    asin: Optional[str] = None,
    sync_id: Optional[UUID] = None,
    error_details: Optional[dict] = None,
    stack_trace: Optional[str] = None,
    severity: str = "error",
) -> Optional[ErrorLog]:
    """Log an error to the database.

    Args:
        db: Database session
        error_type: Type of error (download_error, decryption_error, api_error, etc.)
        error_message: Error message
        error_code: Error code if applicable
        user_id: Associated user ID
        asin: Associated book ASIN
        sync_id: Associated sync ID
        error_details: Detailed error info as dict
        stack_trace: Stack trace if applicable
        severity: Severity level (info, warning, error, critical)

    Returns:
        ErrorLog object if successful, None otherwise
    """
    try:
        error = ErrorLog(
            error_type=error_type,
            error_message=error_message,
            error_code=error_code,
            user_id=user_id,
            asin=asin,
            sync_id=sync_id,
            error_details=error_details,
            stack_trace=stack_trace,
            severity=severity,
        )
        db.add(error)
        await db.flush()
        await db.refresh(error)
        logger.error(f"Logged error: {error_type} - {error_message} (ID: {error.error_id})")
        return error
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
        return None


async def get_error_by_id(db: AsyncSession, error_id: UUID) -> Optional[ErrorLog]:
    """Get error log by ID.

    Args:
        db: Database session
        error_id: Error UUID

    Returns:
        ErrorLog object if found, None otherwise
    """
    try:
        result = await db.execute(select(ErrorLog).where(ErrorLog.error_id == error_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get error: {e}")
        return None


async def get_errors_by_user(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 100,
    unresolved_only: bool = False,
) -> List[ErrorLog]:
    """Get error logs for a user.

    Args:
        db: Database session
        user_id: User UUID
        limit: Maximum number of records to return
        unresolved_only: Only return unresolved errors

    Returns:
        List of ErrorLog objects
    """
    try:
        query = select(ErrorLog).where(ErrorLog.user_id == user_id)
        if unresolved_only:
            query = query.where(~ErrorLog.resolved)
        query = query.order_by(ErrorLog.timestamp.desc()).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get errors for user: {e}")
        return []


async def get_errors_by_asin(
    db: AsyncSession,
    asin: str,
    limit: int = 50,
) -> List[ErrorLog]:
    """Get error logs for a book.

    Args:
        db: Database session
        asin: Book ASIN
        limit: Maximum number of records to return

    Returns:
        List of ErrorLog objects
    """
    try:
        result = await db.execute(
            select(ErrorLog)
            .where(ErrorLog.asin == asin)
            .order_by(ErrorLog.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get errors for ASIN: {e}")
        return []


async def get_errors_by_type(
    db: AsyncSession,
    error_type: str,
    limit: int = 100,
) -> List[ErrorLog]:
    """Get error logs by type.

    Args:
        db: Database session
        error_type: Error type to filter
        limit: Maximum number of records to return

    Returns:
        List of ErrorLog objects
    """
    try:
        result = await db.execute(
            select(ErrorLog)
            .where(ErrorLog.error_type == error_type)
            .order_by(ErrorLog.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get errors by type: {e}")
        return []


async def get_errors_by_severity(
    db: AsyncSession,
    severity: str,
    limit: int = 100,
) -> List[ErrorLog]:
    """Get error logs by severity.

    Args:
        db: Database session
        severity: Severity level (info, warning, error, critical)
        limit: Maximum number of records to return

    Returns:
        List of ErrorLog objects
    """
    try:
        result = await db.execute(
            select(ErrorLog)
            .where(ErrorLog.severity == severity)
            .order_by(ErrorLog.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get errors by severity: {e}")
        return []


async def get_unresolved_errors(
    db: AsyncSession,
    limit: int = 100,
) -> List[ErrorLog]:
    """Get all unresolved errors.

    Args:
        db: Database session
        limit: Maximum number of records to return

    Returns:
        List of unresolved ErrorLog objects
    """
    try:
        result = await db.execute(
            select(ErrorLog)
            .where(~ErrorLog.resolved)
            .order_by(ErrorLog.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get unresolved errors: {e}")
        return []


async def resolve_error(
    db: AsyncSession,
    error_id: UUID,
    resolution_notes: Optional[str] = None,
) -> bool:
    """Mark an error as resolved.

    Args:
        db: Database session
        error_id: Error UUID
        resolution_notes: Notes about how the error was resolved

    Returns:
        True if successful, False otherwise
    """
    try:
        error = await get_error_by_id(db, error_id)
        if not error:
            return False

        error.resolved = True
        error.resolved_at = datetime.now(timezone.utc)
        if resolution_notes:
            error.resolution_notes = resolution_notes

        await db.flush()
        logger.info(f"Resolved error: {error_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to resolve error: {e}")
        return False


async def get_critical_errors(
    db: AsyncSession,
    limit: int = 50,
) -> List[ErrorLog]:
    """Get critical errors for immediate attention.

    Args:
        db: Database session
        limit: Maximum number of records to return

    Returns:
        List of critical ErrorLog objects
    """
    try:
        result = await db.execute(
            select(ErrorLog)
            .where(ErrorLog.severity == "critical")
            .order_by(ErrorLog.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get critical errors: {e}")
        return []


async def get_recent_errors(
    db: AsyncSession,
    hours: int = 24,
    limit: int = 100,
) -> List[ErrorLog]:
    """Get errors from the last N hours.

    Args:
        db: Database session
        hours: Number of hours to look back
        limit: Maximum number of records to return

    Returns:
        List of recent ErrorLog objects
    """
    try:
        cutoff_time = datetime.now(timezone.utc).replace(
            hour=datetime.now(timezone.utc).hour - hours
        )
        result = await db.execute(
            select(ErrorLog)
            .where(ErrorLog.timestamp >= cutoff_time)
            .order_by(ErrorLog.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get recent errors: {e}")
        return []


async def get_error_summary(db: AsyncSession) -> Optional[dict]:
    """Get a summary of all errors.

    Args:
        db: Database session

    Returns:
        Dictionary with error statistics
    """
    try:
        all_errors = await db.execute(select(ErrorLog))
        errors = all_errors.scalars().all()

        if not errors:
            return None

        error_types = {}
        severities = {}
        resolved_count = 0

        for error in errors:
            # Count by type
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1

            # Count by severity
            severities[error.severity] = severities.get(error.severity, 0) + 1

            # Count resolved
            if error.resolved:
                resolved_count += 1

        return {
            "total_errors": len(errors),
            "resolved_errors": resolved_count,
            "unresolved_errors": len(errors) - resolved_count,
            "error_types": error_types,
            "severities": severities,
            "resolution_rate": resolved_count / len(errors) if errors else 0,
        }
    except Exception as e:
        logger.error(f"Failed to get error summary: {e}")
        return None


async def delete_error(db: AsyncSession, error_id: UUID) -> bool:
    """Delete an error record.

    Args:
        db: Database session
        error_id: Error UUID

    Returns:
        True if successful, False otherwise
    """
    try:
        error = await get_error_by_id(db, error_id)
        if not error:
            return False

        await db.delete(error)
        await db.flush()
        logger.info(f"Deleted error: {error_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete error: {e}")
        return False


async def clean_old_resolved_errors(
    db: AsyncSession,
    days: int = 90,
) -> int:
    """Delete resolved errors older than N days.

    Args:
        db: Database session
        days: Age of errors to delete

    Returns:
        Number of errors deleted
    """
    try:
        from datetime import timedelta

        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(ErrorLog).where(
                and_(
                    ErrorLog.resolved,
                    ErrorLog.resolved_at < cutoff_time,
                )
            )
        )
        errors = result.scalars().all()

        for error in errors:
            await db.delete(error)

        await db.flush()
        logger.info(f"Cleaned {len(errors)} old resolved errors")
        return len(errors)
    except Exception as e:
        logger.error(f"Failed to clean old errors: {e}")
        return 0
