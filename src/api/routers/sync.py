"""Sync operation endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ...database.services import sync_service
from ..middleware.error_handler import (
    AuthenticationError,
    AuthorizationError,
    InternalServerError,
    ResourceNotFoundError,
    handle_route_errors,
)
from ..schemas.sync import (
    SyncAcceptedResponse,
    SyncCreate,
    SyncHistoryList,
    SyncResponse,
)
from ..security.auth import get_current_user
from ..utils.auth_utils import get_user_id
from ..utils.generic_handlers import get_paginated_list, get_pagination_params

router = APIRouter()

# Pagination parameters for sync history endpoint
_sync_page, _sync_page_size = get_pagination_params(page_size_default=10, page_size_max=50)


@router.post(
    "/",
    response_model=SyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger library sync",
    description="Start a background sync operation to update user's library from Audible",
    responses={
        202: {"description": "Sync initiated successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("trigger sync")
async def trigger_sync(
    sync_data: SyncCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SyncAcceptedResponse:
    """
    Trigger a new library sync operation.

    Initiates a background sync that will fetch books from Audible, download,
    and decrypt them. The operation runs asynchronously and progress updates
    are sent via WebSocket.

    Args:
        sync_data: Sync parameters (sync_type)
        background_tasks: FastAPI background tasks queue
        current_user: Current authenticated user (from JWT token)
        db: Database session

    Returns:
        SyncAcceptedResponse: Sync ID and initial status (202 Accepted)

    Example:
        POST /api/v1/sync/
        {
            "sync_type": "full"
        }
    """
    user_id = get_user_id(current_user)
    if not user_id:
        raise AuthenticationError("Invalid user authentication")
    logger.info(f"Sync triggered for user {user_id} with type: {sync_data.sync_type}")

    # Create sync history entry using ORM
    sync_history = await sync_service.create_sync_history(
        db=db,
        user_id=UUID(user_id),
        sync_type=sync_data.sync_type,
    )
    await db.commit()

    if not sync_history:
        logger.error(f"Failed to create sync record for user {user_id}")
        raise InternalServerError(f"Failed to create sync record for user {user_id}")

    sync_id = str(sync_history.sync_id)

    # Queue background sync task
    from ..services.background_service import BackgroundTaskService

    background_tasks.add_task(
        BackgroundTaskService.execute_sync_operation,
        user_id=user_id,
        sync_id=sync_id,
        sync_type=sync_data.sync_type,
    )
    logger.info(f"Sync queued for background execution: {sync_id}")

    return SyncAcceptedResponse(
        sync_id=sync_id,
        status="in_progress",
        message="Sync initiated successfully, running in background",
        sync_started_at=datetime.now(timezone.utc),
    )


@router.get(
    "/history",
    response_model=SyncHistoryList,
    summary="Get sync history",
    description="Get user's sync history with pagination",
    responses={
        200: {"description": "Sync history retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("get sync history")
async def get_sync_history(
    current_user: dict = Depends(get_current_user),
    page: int = _sync_page,
    page_size: int = _sync_page_size,
    db: AsyncSession = Depends(get_db_session),
) -> SyncHistoryList:
    """
    Get user's sync history with pagination.

    Retrieves all sync operations performed by the user, ordered by most recent first.

    Args:
        current_user: Current authenticated user (from JWT token)
        page: Page number for pagination (default: 1)
        page_size: Items per page (default: 10, max: 50)
        db: Database session

    Returns:
        SyncHistoryList: Paginated list of sync records

    Example:
        GET /api/v1/sync/history?page=1&page_size=10
    """
    user_id = get_user_id(current_user)
    if not user_id:
        raise AuthenticationError("Invalid user authentication")

    async def get_syncs(**kwargs):
        return await sync_service.get_syncs_by_user(
            db=db, user_id=UUID(kwargs["user_id"]), limit=1000
        )

    result = await get_paginated_list(
        get_items_func=get_syncs,
        response_model=SyncResponse,
        get_items_kwargs={"user_id": user_id},
        user_id=user_id,
        page=page,
        page_size=page_size,
        resource_name="sync records",
    )

    return SyncHistoryList(**result)


@router.get(
    "/{sync_id}",
    response_model=SyncResponse,
    summary="Get sync status",
    description="Get detailed status of a specific sync operation",
    responses={
        200: {"description": "Sync status retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this sync"},
        404: {"description": "Sync not found"},
    },
)
@handle_route_errors("get sync status")
async def get_sync_status(
    sync_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SyncResponse:
    """
    Get detailed status of a specific sync operation.

    Retrieves the current status and statistics for a sync operation.
    User can only access their own sync records.

    Args:
        sync_id: Unique sync identifier
        current_user: Current authenticated user (from JWT token)

    Returns:
        SyncResponse: Complete sync details and status

    Raises:
        ResourceNotFoundError: If sync not found
        AuthorizationError: If sync belongs to another user

    Example:
        GET /api/v1/sync/sync-uuid-123
    """
    user_id = get_user_id(current_user)
    logger.info(f"Fetching sync status: {sync_id} for user: {user_id}")

    # Get sync by ID
    sync = await sync_service.get_sync_by_id(db, UUID(sync_id))

    if not sync:
        logger.warning(f"Sync not found: {sync_id}")
        raise ResourceNotFoundError(f"Sync '{sync_id}' not found")

    # Verify ownership
    if str(sync.user_id) != user_id:
        logger.warning(f"Unauthorized access attempt to sync {sync_id} by user {user_id}")
        raise AuthorizationError("Not authorized to access this sync")

    logger.info(f"Retrieved sync details: {sync_id}")
    return SyncResponse.model_validate(sync, from_attributes=True)
