"""Sync schedule database service layer using SQLAlchemy ORM."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.sync_schedule import SyncSchedule
from src.database.services.base_service import delete_entity, update_entity


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def create_sync_schedule(
    db: AsyncSession,
    user_id: UUID,
    interval_minutes: int,
    action: str,
    enabled: bool = True,
    start_at: Optional[datetime] = None,
) -> Optional[SyncSchedule]:
    """Create a new sync schedule for a user."""
    try:
        normalized_start = _normalize_datetime(start_at)
        now = datetime.now(timezone.utc)
        next_run_at = normalized_start or (now + timedelta(minutes=interval_minutes))

        schedule = SyncSchedule(
            user_id=user_id,
            interval_minutes=interval_minutes,
            action=action,
            enabled=enabled,
            next_run_at=next_run_at,
        )
        db.add(schedule)
        await db.flush()
        await db.refresh(schedule)
        logger.info(f"Created sync schedule {schedule.schedule_id} for user {user_id}")
        return schedule
    except Exception as e:
        logger.error(f"Failed to create sync schedule: {e}")
        return None


async def get_sync_schedules_by_user(
    db: AsyncSession,
    user_id: UUID,
) -> List[SyncSchedule]:
    """Get all sync schedules for a user."""
    try:
        result = await db.execute(
            select(SyncSchedule)
            .where(SyncSchedule.user_id == user_id)
            .order_by(SyncSchedule.created_at.desc())
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get sync schedules for user {user_id}: {e}")
        return []


async def get_sync_schedule_by_id(
    db: AsyncSession,
    schedule_id: UUID,
) -> Optional[SyncSchedule]:
    """Get a sync schedule by ID."""
    try:
        result = await db.execute(
            select(SyncSchedule).where(SyncSchedule.schedule_id == schedule_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get sync schedule {schedule_id}: {e}")
        return None


async def get_due_sync_schedules(
    db: AsyncSession,
    now: datetime,
) -> List[SyncSchedule]:
    """Get schedules that are due to run."""
    try:
        result = await db.execute(
            select(SyncSchedule).where(
                SyncSchedule.enabled.is_(True),
                SyncSchedule.next_run_at <= now,
            )
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get due sync schedules: {e}")
        return []


async def update_schedule_run(
    db: AsyncSession,
    schedule_id: UUID,
    last_run_at: datetime,
    next_run_at: datetime,
) -> bool:
    """Update the last/next run timestamps for a schedule."""
    try:
        schedule = await get_sync_schedule_by_id(db, schedule_id)
        if not schedule:
            return False

        schedule.last_run_at = last_run_at
        schedule.next_run_at = next_run_at
        await db.flush()
        return True
    except Exception as e:
        logger.error(f"Failed to update sync schedule {schedule_id}: {e}")
        return False


async def update_sync_schedule(
    db: AsyncSession,
    schedule_id: UUID,
    user_id: UUID,
    updates: Dict[str, Any],
) -> Optional[SyncSchedule]:
    """Update schedule fields for a user-owned schedule."""
    schedule = await get_sync_schedule_by_id(db, schedule_id)
    if not schedule or schedule.user_id != user_id:
        return None

    updates = {key: value for key, value in updates.items() if value is not None}
    start_at = updates.pop("start_at", None)
    if start_at is not None:
        updates["next_run_at"] = _normalize_datetime(start_at)
    elif "interval_minutes" in updates:
        now = datetime.now(timezone.utc)
        updates["next_run_at"] = now + timedelta(minutes=updates["interval_minutes"])

    if not updates:
        return schedule

    success = await update_entity(
        db=db,
        entity=schedule,
        updates=updates,
        entity_name="SyncSchedule",
        entity_id=schedule_id,
    )
    if not success:
        return None
    return schedule


async def delete_sync_schedule(
    db: AsyncSession,
    schedule_id: UUID,
    user_id: UUID,
) -> bool:
    """Delete a schedule owned by a user."""
    schedule = await get_sync_schedule_by_id(db, schedule_id)
    if not schedule or schedule.user_id != user_id:
        return False
    return await delete_entity(
        db=db,
        entity=schedule,
        entity_name="SyncSchedule",
        entity_id=schedule_id,
    )
