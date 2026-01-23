"""Task monitoring endpoints for active downloads, decryptions, and syncs."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.error_handler import ResourceNotFoundError, handle_route_errors
from src.api.schemas.task_monitor import (
    ActiveTaskResponse,
    ActiveTasksList,
    TaskCancelResponse,
    TaskType,
)
from src.api.security.auth import get_current_user
from src.database.engine import get_db_session
from src.database.models.user import User
from src.database.services import task_monitor_service

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
            error_message=task["error_message"],
        )
        for task in tasks_data["decryptions"]
    ]

    syncs = [
        ActiveTaskResponse(
            task_id=task["task_id"],
            task_type=TaskType.SYNC,
            status=task["status"],
            started_at=task["started_at"],
            sync_type=task["sync_type"],
            books_found=task["books_found"],
            books_added=task["books_added"],
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
        success, task_type, current_status, message = (
            await task_monitor_service.cancel_task(
                db=db,
                task_id=task_uuid,
                user_id=user_id,
            )
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
