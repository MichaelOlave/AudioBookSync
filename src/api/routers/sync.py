"""Sync operation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from loguru import logger
from datetime import datetime, timezone

from ...database.db_sync import sync_ops
from ..security.auth import get_current_user
from ..schemas.sync import (
    SyncCreate,
    SyncResponse,
    SyncHistoryList,
    SyncAcceptedResponse,
)
from ..middleware.error_handler import ResourceNotFoundError

router = APIRouter()


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
async def trigger_sync(
    sync_data: SyncCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
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

    Returns:
        SyncAcceptedResponse: Sync ID and initial status (202 Accepted)

    Example:
        POST /api/v1/sync/
        {
            "sync_type": "full"
        }
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )
        logger.info(
            f"Sync triggered for user {user_id} with type: {sync_data.sync_type}"
        )

        # Create sync history entry
        sync_id = sync_ops.create_sync_history(
            user_id=user_id,
            sync_type=sync_data.sync_type,
        )

        if not sync_id:
            logger.error(f"Failed to create sync record for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate sync",
            )

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error triggering sync for user {current_user.get('user_id')}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate sync",
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
async def get_sync_history(
    current_user: dict = Depends(get_current_user),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (starting from 1)",
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Number of items per page (1-50)",
    ),
) -> SyncHistoryList:
    """
    Get user's sync history with pagination.

    Retrieves all sync operations performed by the user, ordered by most recent first.

    Args:
        current_user: Current authenticated user (from JWT token)
        page: Page number for pagination (default: 1)
        page_size: Items per page (default: 10, max: 50)

    Returns:
        SyncHistoryList: Paginated list of sync records

    Example:
        GET /api/v1/sync/history?page=1&page_size=10
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )
        logger.info(f"Fetching sync history for user: {user_id}")

        # Get sync history with larger limit to support pagination
        all_syncs = sync_ops.get_user_sync_history(user_id, limit=1000)

        # Calculate pagination
        total = len(all_syncs)
        pages = (total + page_size - 1) // page_size if total > 0 else 0

        # Validate page number
        if page > pages and total > 0:
            logger.warning(f"Page {page} exceeds max pages {pages} for user {user_id}")
            page = pages

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_syncs = all_syncs[start_idx:end_idx]

        # Convert to SyncResponse objects
        items = [SyncResponse(**sync) for sync in paginated_syncs]

        logger.info(
            f"Retrieved {len(items)} sync records for user {user_id} (page {page}/{pages})"
        )

        return SyncHistoryList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    except Exception as e:
        logger.error(
            f"Error fetching sync history for user {current_user.get('user_id')}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync history",
        )


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
async def get_sync_status(
    sync_id: str,
    current_user: dict = Depends(get_current_user),
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
    try:
        user_id = current_user.get("user_id")
        logger.info(f"Fetching sync status: {sync_id} for user: {user_id}")

        # Get sync by ID
        sync = sync_ops.get_sync_by_id(sync_id)

        if not sync:
            logger.warning(f"Sync not found: {sync_id}")
            raise ResourceNotFoundError(f"Sync '{sync_id}' not found")

        # Verify ownership
        if sync.get("user_id") != user_id:
            logger.warning(
                f"Unauthorized access attempt to sync {sync_id} by user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this sync",
            )

        logger.info(f"Retrieved sync details: {sync_id}")
        return SyncResponse(**sync)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sync {sync_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sync status",
        )
