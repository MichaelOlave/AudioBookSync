"""Decryption management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from loguru import logger

from ...database.db_decryptions import decryption_ops
from ...database.db_downloads import download_ops
from ..security.auth import get_current_user
from ..schemas.decryption import (
    DecryptCreate,
    DecryptResponse,
    DecryptList,
)
from ..services.background_service import BackgroundTaskService
from ..middleware.error_handler import ResourceNotFoundError

router = APIRouter()


@router.post(
    "/",
    response_model=DecryptResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger book decryption",
    description="Initiate a background decryption for a downloaded audiobook",
    responses={
        202: {"description": "Decryption initiated successfully"},
        400: {"description": "Invalid book data or download not completed"},
        401: {"description": "Not authenticated"},
    },
)
async def trigger_decrypt(
    decrypt_data: DecryptCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
) -> DecryptResponse:
    """
    Trigger a book decryption operation in background.

    Validates that the book has been downloaded and then queues a background task
    to decrypt the audiobook. Returns immediately with 202 Accepted status.

    Args:
        decrypt_data: Book information (asin, title)
        background_tasks: FastAPI background tasks queue
        current_user: Authenticated user from JWT token

    Returns:
        DecryptResponse: Initial decryption record with status 'pending'

    Raises:
        HTTPException: If book not downloaded or record creation fails

    Example:
        POST /api/v1/decryptions/
        {
            "asin": "B084L6Z6M3",
            "title": "Becoming"
        }

        Response:
        {
            "decryption_id": "550e8400-e29b-41d4-a716-446655440000",
            "asin": "B084L6Z6M3",
            "status": "pending",
            "message": "Decryption initiated"
        }
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )

        logger.info(f"Decryption triggered for {decrypt_data.asin} by user {user_id}")

        # Verify download exists and is completed
        download = download_ops.get_download_by_asin(decrypt_data.asin)
        if not download:
            logger.warning(f"Download not found for {decrypt_data.asin}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book must be downloaded before decryption",
            )

        if download.get("status") != "completed":
            logger.warning(
                f"Download not completed for {decrypt_data.asin}: {download.get('status')}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Download must be completed before decryption (current status: {download.get('status')})",
            )

        # Create decryption status record in database
        decryption_id = decryption_ops.create_decryption_status(
            asin=decrypt_data.asin,
            download_id=download.get("download_id"),
            status="pending",
        )

        if not decryption_id:
            logger.error(f"Failed to create decryption record for {decrypt_data.asin}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create decryption record",
            )

        # Queue background decryption task
        background_tasks.add_task(
            BackgroundTaskService.execute_decrypt_operation,
            user_id=user_id,
            decryption_id=decryption_id,
            book=decrypt_data.dict(),
        )

        logger.info(f"Decryption queued: {decryption_id}")

        return DecryptResponse(
            decryption_id=decryption_id,
            asin=decrypt_data.asin,
            status="pending",
            message="Decryption initiated",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering decryption: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate decryption",
        )


@router.get(
    "/",
    response_model=DecryptList,
    summary="List user's decryptions",
    description="Get paginated list of decryptions for the current user",
    responses={
        200: {"description": "Decryptions retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_decryptions(
    current_user: dict = Depends(get_current_user),
    status_filter: str = Query(
        None,
        alias="status",
        description="Filter by status (pending, decrypting, completed, failed, cancelled)",
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
) -> DecryptList:
    """
    Get list of decryptions for current user with pagination.

    Retrieves all decryptions (optionally filtered by status) for the authenticated user.
    Results are paginated and ordered by most recent first.

    Args:
        current_user: Authenticated user from JWT token
        status_filter: Optional status filter
        page: Page number for pagination (default: 1)
        page_size: Items per page (default: 10, max: 50)

    Returns:
        DecryptList: Paginated list of decryption records

    Example:
        GET /api/v1/decryptions/?status=completed&page=1&page_size=10
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )

        logger.info(f"Fetching decryptions for user {user_id}")

        # Get decryptions with pagination
        # Note: db_decryptions.py needs to be extended with get_user_decryptions()
        decryptions = decryption_ops.get_user_decryptions(
            user_id=user_id,
            status=status_filter,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        # Get total count
        total = decryption_ops.count_user_decryptions(user_id, status_filter)

        # Calculate pages
        pages = (total + page_size - 1) // page_size if total > 0 else 1

        # Validate page number
        if page > pages and total > 0:
            logger.warning(f"Page {page} exceeds max pages {pages}")
            page = pages

        # Convert to response objects
        items = [DecryptResponse(**decryption) for decryption in decryptions]

        logger.info(
            f"Retrieved {len(items)} decryptions for user {user_id} (page {page}/{pages})"
        )

        return DecryptList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching decryptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve decryptions",
        )


@router.get(
    "/{decryption_id}",
    response_model=DecryptResponse,
    summary="Get decryption status",
    description="Get detailed status of a specific decryption",
    responses={
        200: {"description": "Decryption status retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this decryption"},
        404: {"description": "Decryption not found"},
    },
)
async def get_decryption_status(
    decryption_id: str,
    current_user: dict = Depends(get_current_user),
) -> DecryptResponse:
    """
    Get detailed status of a specific decryption.

    Retrieves current status and metadata for a decryption operation.
    User can only access their own decryptions.

    Args:
        decryption_id: Unique decryption identifier
        current_user: Authenticated user from JWT token

    Returns:
        DecryptResponse: Complete decryption record

    Raises:
        ResourceNotFoundError: If decryption not found
        HTTPException: If decryption belongs to another user

    Example:
        GET /api/v1/decryptions/550e8400-e29b-41d4-a716-446655440000
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user authentication",
            )

        logger.info(f"Fetching decryption status: {decryption_id} for user {user_id}")

        # Get decryption by ID
        decryption = decryption_ops.get_decryption_by_id(decryption_id)

        if not decryption:
            logger.warning(f"Decryption not found: {decryption_id}")
            raise ResourceNotFoundError(f"Decryption '{decryption_id}' not found")

        # Verify ownership by checking associated book user_id
        # (requires join with books table, which db_decryptions.py needs to support)
        if decryption.get("user_id") != user_id:
            logger.warning(
                f"Unauthorized access attempt to decryption {decryption_id} by user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this decryption",
            )

        logger.info(f"Retrieved decryption details: {decryption_id}")
        return DecryptResponse(**decryption)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching decryption {decryption_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve decryption status",
        )
