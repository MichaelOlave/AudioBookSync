"""Download management endpoints."""

from fastapi import APIRouter, Depends, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from loguru import logger

from ...database.services import download_service
from ...database.engine import get_db_session
from ...database.models.user import User
from ..security.auth import get_current_user
from ..schemas.download import (
    DownloadCreate,
    DownloadResponse,
    DownloadList,
)
from ..services.background_service import BackgroundTaskService
from ..middleware.error_handler import ResourceNotFoundError, handle_route_errors
from ..utils.generic_handlers import get_paginated_list

router = APIRouter()


@router.post(
    "/",
    response_model=DownloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger book download",
    description="Initiate a background download for a specific book",
    responses={
        202: {"description": "Download initiated successfully"},
        400: {"description": "Invalid book data"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("trigger download")
async def trigger_download(
    download_data: DownloadCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DownloadResponse:
    """
    Trigger a book download operation in background.

    Validates book information and queues a background task to download the audiobook.
    Returns immediately with 202 Accepted status.

    Args:
        download_data: Book information (asin, title)
        background_tasks: FastAPI background tasks queue
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        DownloadResponse: Initial download record with status 'pending'

    Raises:
        HTTPException: If download record creation fails

    Example:
        POST /api/v1/downloads/
        {
            "asin": "B084L6Z6M3",
            "title": "Becoming"
        }

        Response:
        {
            "download_id": "550e8400-e29b-41d4-a716-446655440000",
            "asin": "B084L6Z6M3",
            "status": "pending",
            "message": "Download initiated"
        }
    """
    logger.info(f"Download triggered for {download_data.asin} by user {current_user.user_id}")

    # Create download status record in database
    download = await download_service.create_download_status(
        db=db,
        asin=download_data.asin,
        status="pending",
    )

    if not download:
        logger.error(f"Failed to create download record for {download_data.asin}")
        raise ResourceNotFoundError(f"Failed to create download record for {download_data.asin}")

    await db.commit()

    # Queue background download task
    background_tasks.add_task(
        BackgroundTaskService.execute_download_operation,
        user_id=str(current_user.user_id),
        download_id=download.download_id,
        book=download_data.dict(),
    )

    logger.info(f"Download queued: {download.download_id}")

    return DownloadResponse(
        download_id=download.download_id,
        asin=download_data.asin,
        status="pending",
        message="Download initiated",
    )


@router.get(
    "/",
    response_model=DownloadList,
    summary="List user's downloads",
    description="Get paginated list of downloads for the current user",
    responses={
        200: {"description": "Downloads retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("list downloads")
async def list_downloads(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    status_filter: str = Query(
        None,
        alias="status",
        description="Filter by status (pending, downloading, completed, failed, cancelled)",
    ),
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
) -> DownloadList:
    """
    Get list of downloads for current user with pagination.

    Retrieves all downloads (optionally filtered by status) for the authenticated user.
    Results are paginated and ordered by most recent first.

    Args:
        current_user: Authenticated user from JWT token
        db: Database session
        status_filter: Optional status filter
        page: Page number for pagination (default: 1)
        page_size: Items per page (default: 10, max: 50)

    Returns:
        DownloadList: Paginated list of download records

    Example:
        GET /api/v1/downloads/?status=completed&page=1&page_size=10
    """
    result = await get_paginated_list(
        get_items_func=download_service.get_downloads_by_user,
        response_model=DownloadResponse,
        get_items_kwargs={
            "db": db,
            "user_id": str(current_user.user_id),
            "status": status_filter,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        },
        user_id=str(current_user.user_id),
        page=page,
        page_size=page_size,
        count_func=download_service.count_downloads_by_user,
        count_kwargs={
            "db": db,
            "user_id": str(current_user.user_id),
            "status": status_filter,
        },
        resource_name="downloads",
    )

    return DownloadList(**result)


@router.get(
    "/{download_id}",
    response_model=DownloadResponse,
    summary="Get download status",
    description="Get detailed status of a specific download",
    responses={
        200: {"description": "Download status retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this download"},
        404: {"description": "Download not found"},
    },
)
@handle_route_errors("get download status")
async def get_download_status(
    download_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DownloadResponse:
    """
    Get detailed status of a specific download.

    Retrieves current status and metadata for a download operation.
    User can only access their own downloads.

    Args:
        download_id: Unique download identifier
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        DownloadResponse: Complete download record

    Raises:
        ResourceNotFoundError: If download not found
        HTTPException: If download belongs to another user

    Example:
        GET /api/v1/downloads/550e8400-e29b-41d4-a716-446655440000
    """
    logger.info(f"Fetching download status: {download_id} for user {current_user.user_id}")

    # Get download by ID with user authorization check
    download = await download_service.get_download_by_id_for_user(
        db=db,
        download_id=UUID(download_id),
        user_id=str(current_user.user_id),
    )

    if not download:
        logger.warning(f"Download not found or user not authorized: {download_id}")
        raise ResourceNotFoundError(f"Download '{download_id}' not found")

    logger.info(f"Retrieved download details: {download_id}")
    return DownloadResponse.from_orm(download)
