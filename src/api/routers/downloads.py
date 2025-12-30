"""Download management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from loguru import logger

from ...database.db_downloads import download_ops
from ..security.auth import get_current_user
from ..schemas.download import (
    DownloadCreate,
    DownloadResponse,
    DownloadList,
)
from ..services.background_service import BackgroundTaskService
from ..middleware.error_handler import ResourceNotFoundError

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
async def trigger_download(
    download_data: DownloadCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> DownloadResponse:
    """
    Trigger a book download operation in background.

    Validates book information and queues a background task to download the audiobook.
    Returns immediately with 202 Accepted status.

    Args:
        download_data: Book information (asin, title)
        background_tasks: FastAPI background tasks queue
        current_user: Authenticated user from JWT token

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
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )

        logger.info(f"Download triggered for {download_data.asin} by user {user_id}")

        # Create download status record in database
        download_id = download_ops.create_download_status(
            asin=download_data.asin,
            status="pending",
        )

        if not download_id:
            logger.error(f"Failed to create download record for {download_data.asin}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create download record",
            )

        # Queue background download task
        background_tasks.add_task(
            BackgroundTaskService.execute_download_operation,
            user_id=user_id,
            download_id=download_id,
            book=download_data.dict(),
        )

        logger.info(f"Download queued: {download_id}")

        return DownloadResponse(
            download_id=download_id,
            asin=download_data.asin,
            status="pending",
            message="Download initiated",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate download",
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
async def list_downloads(
    current_user: dict = Depends(get_current_user),
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
        status_filter: Optional status filter
        page: Page number for pagination (default: 1)
        page_size: Items per page (default: 10, max: 50)

    Returns:
        DownloadList: Paginated list of download records

    Example:
        GET /api/v1/downloads/?status=completed&page=1&page_size=10
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )

        logger.info(f"Fetching downloads for user {user_id}")

        # Get downloads with pagination
        # Note: db_downloads.py needs to be extended with get_user_downloads()
        # For now, using basic query approach
        downloads = download_ops.get_user_downloads(
            user_id=user_id,
            status=status_filter,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        # Get total count
        total = download_ops.count_user_downloads(user_id, status_filter)

        # Calculate pages
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        # Validate page number
        if page > pages and total > 0:
            logger.warning(f"Page {page} exceeds max pages {pages}")
            page = pages

        # Convert to response objects
        items = [DownloadResponse(**download) for download in downloads]

        logger.info(
            f"Retrieved {len(items)} downloads for user {user_id} (page {page}/{pages})"
        )

        return DownloadList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching downloads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve downloads",
        )


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
async def get_download_status(
    download_id: str,
    current_user: dict = Depends(get_current_user),
) -> DownloadResponse:
    """
    Get detailed status of a specific download.

    Retrieves current status and metadata for a download operation.
    User can only access their own downloads.

    Args:
        download_id: Unique download identifier
        current_user: Authenticated user from JWT token

    Returns:
        DownloadResponse: Complete download record

    Raises:
        ResourceNotFoundError: If download not found
        HTTPException: If download belongs to another user

    Example:
        GET /api/v1/downloads/550e8400-e29b-41d4-a716-446655440000
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )

        logger.info(f"Fetching download status: {download_id} for user {user_id}")

        # Get download by ID
        download = download_ops.get_download_by_id(download_id)

        if not download:
            logger.warning(f"Download not found: {download_id}")
            raise ResourceNotFoundError(f"Download '{download_id}' not found")

        # Verify ownership by checking associated book user_id
        # (requires join with books table, which db_downloads.py needs to support)
        if download.get("user_id") != user_id:
            logger.warning(
                f"Unauthorized access attempt to download {download_id} by user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this download",
            )

        logger.info(f"Retrieved download details: {download_id}")
        return DownloadResponse(**download)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching download {download_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve download status",
        )
