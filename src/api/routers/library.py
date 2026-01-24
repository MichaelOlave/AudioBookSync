"""User library endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ...database.models.user import User
from ...database.services import book_service
from ..services.audible_library_service import fetch_audible_library_to_db
from ..middleware.error_handler import ResourceNotFoundError, handle_route_errors
from ..schemas.book import BookDashboardResponse, BookList, BookResponse
from ..security.auth import get_current_user
from ..utils.auth_utils import get_user_id
from ..utils.generic_handlers import (
    get_paginated_list,
    get_pagination_params,
    verify_book_ownership,
)

router = APIRouter()

# Pagination parameters for library endpoint
_lib_page, _lib_page_size = get_pagination_params(page_size_default=50, page_size_max=100)


@router.get(
    "/",
    response_model=BookList,
    summary="Get user's library",
    description="Get paginated list of books in user's library",
    responses={
        200: {"description": "Library retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("get library")
async def get_library(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    page: int = _lib_page,
    page_size: int = _lib_page_size,
) -> BookList:
    """
    Get user's audiobook library with pagination.

    Retrieves all books owned by the current user, ordered by purchase date.

    Args:
        current_user: Current authenticated user (from JWT token)
        db: Database session
        page: Page number for pagination (default: 1)
        page_size: Items per page (default: 50, max: 100)

    Returns:
        BookList: Paginated list of user's books with metadata

    Example:
        GET /api/v1/library?page=1&page_size=50
    """

    async def get_books(**kwargs):
        return await book_service.get_books_by_user(kwargs["db"], kwargs["user_id"])

    result = await get_paginated_list(
        get_items_func=get_books,
        response_model=BookResponse,
        get_items_kwargs={
            "db": db,
            "user_id": get_user_id(current_user),
        },
        user_id=get_user_id(current_user),
        page=page,
        page_size=page_size,
        resource_name="books",
    )

    return BookList(**result)


@router.get(
    "/audible/fetch",
    summary="Fetch library from Audible and save to database",
    description="Fetch user's audiobook library from Audible API and save books to database",
    responses={
        200: {"description": "Library fetched and saved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Audible credentials not configured"},
        500: {"description": "Failed to fetch from Audible"},
    },
)
@handle_route_errors("fetch Audible library")
async def fetch_audible_library(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    num_results: int = Query(
        default=1000,
        ge=1,
        le=1000,
        description="Number of results to fetch (1-1000)",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number to fetch (starting from 1)",
    ),
) -> Dict[str, Any]:
    """
    Fetch user's audiobook library from Audible API and save to database.

    Uses stored Audible credentials to retrieve the complete library
    from Audible's servers and saves book data to the database without
    downloading the audiobook files.

    Args:
        current_user: Current authenticated user (from JWT token)
        db: Database session
        num_results: Number of books to fetch (default: 1000, max: 1000)
        page: Page number to fetch (default: 1)

    Returns:
        Dict with save statistics including number of books saved

    Raises:
        HTTPException: If credentials not found or API call fails

    Example:
        GET /api/v1/library/audible/fetch?num_results=100
    """
    user_id = get_user_id(current_user)
    logger.info(f"Fetching Audible library for user: {user_id}")

    return await fetch_audible_library_to_db(
        db=db,
        user_id=user_id,
        num_results=num_results,
        page=page,
    )


@router.get(
    "/dashboard",
    response_model=List[BookDashboardResponse],
    summary="Get dashboard books",
    description="Get all books with metadata for dashboard views",
    responses={
        200: {"description": "Dashboard books retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("get dashboard books")
async def get_dashboard_books(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    downloaded_only: bool = Query(
        default=False,
        description="When true, only return books marked as downloaded",
    ),
) -> List[BookDashboardResponse]:
    """
    Get full library details for dashboard use.

    Returns all books with extended metadata when available.
    Optionally filters to downloaded books when requested.
    """
    user_id = get_user_id(current_user)
    logger.info(f"Fetching dashboard books for user: {user_id}")

    rows = await book_service.get_books_with_metadata_by_user(
        db,
        user_id,
        downloaded_only=downloaded_only,
    )
    return [
        BookDashboardResponse(book=book, metadata=metadata)
        for book, metadata in rows
    ]


@router.get(
    "/{asin}",
    response_model=BookResponse,
    summary="Get book details",
    description="Get detailed information about a specific book",
    responses={
        200: {"description": "Book details retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this book"},
        404: {"description": "Book not found"},
    },
)
@handle_route_errors("get book details")
async def get_book_details(
    asin: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BookResponse:
    """
    Get detailed information about a specific audiobook.

    Retrieves book details by ASIN (Amazon Standard Identification Number).
    User can only access their own books.

    Args:
        asin: Amazon Standard Identification Number (10-character code)
        current_user: Current authenticated user (from JWT token)
        db: Database session

    Returns:
        BookResponse: Complete book details with metadata

    Raises:
        ResourceNotFoundError: If book not found
        AuthorizationError: If book belongs to another user

    Example:
        GET /api/v1/library/B084L6Z6M3
    """
    user_id = get_user_id(current_user)
    logger.info(f"Fetching book details: {asin} for user: {user_id}")

    # Get book by ASIN
    book = await book_service.get_book_by_asin(db, asin)

    if not book:
        logger.warning(f"Book not found: {asin}")
        raise ResourceNotFoundError(f"Book '{asin}' not found")

    verify_book_ownership(book, user_id, asin)

    logger.info(f"Retrieved book details: {asin}")
    return BookResponse.from_orm(book)
