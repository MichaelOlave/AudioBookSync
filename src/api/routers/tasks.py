"""Task monitoring endpoints for active downloads, decryptions, and syncs."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.error_handler import (
    InternalServerError,
    ResourceNotFoundError,
    ValidationError,
    handle_route_errors,
)
from src.api.schemas.common import MessageResponse
from src.api.schemas.sync_schedule import (
    SyncScheduleCreate,
    SyncScheduleList,
    SyncScheduleResponse,
    SyncScheduleUpdate,
)
from src.api.schemas.task_monitor import (
    ActiveTaskResponse,
    ActiveTasksList,
    TaskCancelResponse,
    TaskType,
)
from src.api.security.auth import get_current_user
from src.core.config import Config
from src.database.engine import get_db_session
from src.database.models.user import User
from src.database.services import sync_schedule_service, task_monitor_service

router = APIRouter()


@router.get(
    "/active",
    response_model=ActiveTasksList,
    summary="Get active tasks",
    description="Get all currently running tasks (downloads, decryptions, syncs) for the current user",
    responses={
        200: {"description": "Active tasks retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("get active tasks")
async def get_active_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ActiveTasksList:
    """
    Get all active tasks for the current user.

    Returns downloads with status='downloading', decryptions with status='decrypting',
    and syncs with status='in_progress'.
    """
    user_id = str(current_user.user_id)

    logger.info(f"Fetching active tasks for user {user_id}")

    # Get active tasks from service
    tasks_data = await task_monitor_service.get_active_tasks_by_user(db, user_id)

    # Transform to response format
    downloads = [
        ActiveTaskResponse(
            task_id=task["task_id"],
            task_type=TaskType.DOWNLOAD,
            status=task["status"],
            asin=task["asin"],
            title=task["title"],
            progress_percentage=None,
            started_at=task["started_at"],
            attempt_number=task["attempt_number"],
            sync_type=None,
            books_found=None,
            books_added=None,
            error_message=task["error_message"],
        )
        for task in tasks_data["downloads"]
    ]

    decryptions = [
        ActiveTaskResponse(
            task_id=task["task_id"],
            task_type=TaskType.DECRYPTION,
            status=task["status"],
            asin=task["asin"],
            title=task["title"],
            progress_percentage=None,
            started_at=task["started_at"],
            attempt_number=task.get("attempt_number"),
            sync_type=None,
            books_found=None,
            books_added=None,
            error_message=task.get("error_message"),
        )
        for task in tasks_data["decryptions"]
    ]

    syncs = [
        ActiveTaskResponse(
            task_id=task["task_id"],
            task_type=TaskType.SYNC,
            status=task["status"],
            asin=None,
            title=None,
            progress_percentage=None,
            started_at=task["started_at"],
            attempt_number=None,
            sync_type=task["sync_type"],
            books_found=task["books_found"],
            books_added=task["books_added"],
            error_message=task.get("error_message"),
        )
        for task in tasks_data["syncs"]
    ]

    total_active = len(downloads) + len(decryptions) + len(syncs)

    logger.info(f"Found {total_active} active tasks for user {user_id}")

    return ActiveTasksList(
        downloads=downloads,
        decryptions=decryptions,
        syncs=syncs,
        total_active=total_active,
    )


@router.post(
    "/{task_id}/cancel",
    response_model=TaskCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel task",
    description="Cancel a running task by ID. Works for downloads, decryptions, and syncs.",
    responses={
        200: {"description": "Task cancelled successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Task not found"},
        409: {"description": "Task already completed or cancelled"},
    },
)
@handle_route_errors("cancel task")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> TaskCancelResponse:
    """
    Cancel a task by ID.

    Updates the task status to 'cancelled' in the database.
    The task will be marked as cancelled but may take a moment to actually stop.
    """
    user_id = str(current_user.user_id)

    logger.info(f"Attempting to cancel task {task_id} for user {user_id}")

    # Validate UUID
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise ResourceNotFoundError(f"Invalid task ID format: {task_id}")

    # Cancel the task
    try:
        success, task_type, current_status, message = await task_monitor_service.cancel_task(
            db=db,
            task_id=task_uuid,
            user_id=user_id,
        )

        logger.info(f"Task {task_id} cancellation result: {message}")

        return TaskCancelResponse(
            task_id=task_id,
            task_type=TaskType(task_type),
            status=current_status,
            message=message,
            success=success,
        )

    except ValueError as e:
        logger.warning(f"Task {task_id} not found: {e}")
        raise ResourceNotFoundError(str(e))


@router.post(
    "/schedules",
    response_model=SyncScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create scheduled sync",
    description=(
        "Create a recurring schedule to check Audible and optionally download missing books."
    ),
    responses={
        201: {"description": "Schedule created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
@handle_route_errors("create sync schedule")
async def create_sync_schedule(
    schedule_data: SyncScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SyncScheduleResponse:
    """Create a scheduled sync for the current user."""
    if not Config.USE_CELERY_TASKS:
        raise ValidationError(
            "Scheduled syncs require Celery tasks. Set USE_CELERY_TASKS=true and run Celery beat."
        )

    schedule = await sync_schedule_service.create_sync_schedule(
        db=db,
        user_id=current_user.user_id,
        interval_minutes=schedule_data.interval_minutes,
        action=schedule_data.action.value,
        enabled=schedule_data.enabled,
        start_at=schedule_data.start_at,
    )

    if not schedule:
        raise InternalServerError("Failed to create sync schedule")

    await db.commit()
    return SyncScheduleResponse.model_validate(schedule, from_attributes=True)


@router.get(
    "/schedules",
    response_model=SyncScheduleList,
    summary="List scheduled syncs",
    description="List all scheduled sync tasks for the current user.",
    responses={
        200: {"description": "Schedules retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("list sync schedules")
async def list_sync_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SyncScheduleList:
    """List scheduled syncs for the current user."""
    schedules = await sync_schedule_service.get_sync_schedules_by_user(
        db=db,
        user_id=current_user.user_id,
    )
    items = [
        SyncScheduleResponse.model_validate(schedule, from_attributes=True)
        for schedule in schedules
    ]
    return SyncScheduleList(items=items, total=len(items))


@router.patch(
    "/schedules/{schedule_id}",
    response_model=SyncScheduleResponse,
    summary="Update scheduled sync",
    description="Update schedule settings (interval, action, enable/disable, next run).",
    responses={
        200: {"description": "Schedule updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Schedule not found"},
        422: {"description": "Validation error"},
    },
)
@handle_route_errors("update sync schedule")
async def update_sync_schedule(
    schedule_id: str,
    schedule_data: SyncScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SyncScheduleResponse:
    """Update a scheduled sync for the current user."""
    try:
        schedule_uuid = UUID(schedule_id)
    except ValueError:
        raise ResourceNotFoundError(f"Invalid schedule ID format: {schedule_id}")

    updates = {
        "interval_minutes": schedule_data.interval_minutes,
        "action": schedule_data.action.value if schedule_data.action else None,
        "enabled": schedule_data.enabled,
        "start_at": schedule_data.start_at,
    }
    if all(value is None for value in updates.values()):
        raise ValidationError("No schedule fields provided for update")

    schedule = await sync_schedule_service.update_sync_schedule(
        db=db,
        schedule_id=schedule_uuid,
        user_id=current_user.user_id,
        updates=updates,
    )
    if not schedule:
        raise ResourceNotFoundError("Sync schedule not found")

    await db.commit()
    return SyncScheduleResponse.model_validate(schedule, from_attributes=True)


@router.delete(
    "/schedules/{schedule_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete scheduled sync",
    description="Delete a scheduled sync for the current user.",
    responses={
        200: {"description": "Schedule deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Schedule not found"},
    },
)
@handle_route_errors("delete sync schedule")
async def delete_sync_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Delete a scheduled sync for the current user."""
    try:
        schedule_uuid = UUID(schedule_id)
    except ValueError:
        raise ResourceNotFoundError(f"Invalid schedule ID format: {schedule_id}")

    success = await sync_schedule_service.delete_sync_schedule(
        db=db,
        schedule_id=schedule_uuid,
        user_id=current_user.user_id,
    )
    if not success:
        raise ResourceNotFoundError("Sync schedule not found")

    await db.commit()
    return MessageResponse(message="Sync schedule deleted", success=True)
